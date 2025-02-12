from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self

from typing import Any, Final, List, Mapping, Optional, Union

from PIL import Image

from viam.proto.common import PointCloudObject
from viam.proto.service.vision import Classification, Detection
from viam.resource.types import RESOURCE_NAMESPACE_RDK, RESOURCE_TYPE_SERVICE
from viam.utils import ValueTypes


from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.services.vision import Vision, CaptureAllResult
from viam.proto.service.vision import GetPropertiesResponse
from viam.components.camera import Camera, ViamImage
from viam.logging import getLogger
from viam.media.utils.pil import viam_to_pil_image

import modal
from PIL import Image

LOGGER = getLogger(__name__)

class moondream(Vision, Reconfigurable):
    
    """
    Vision represents a Vision service.
    """
    

    MODEL: ClassVar[Model] = Model(ModelFamily("mcvella", "vision"), "moondream-modal")
    
    model: None
    gaze_detection: bool = False

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        return

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        self.DEPS = dependencies
        self.model = modal.Cls.lookup("moondream", "Moondream")

        self.gaze_detection = config.attributes.fields["gaze_detection"].bool_value or False
        self.default_class = config.attributes.fields["default_class"].string_value or "person"
        self.default_question = config.attributes.fields["default_question"].string_value or "describe this image"

        return
        
    async def get_cam_image(
        self,
        camera_name: str
    ) -> ViamImage:
        actual_cam = self.DEPS[Camera.get_resource_name(camera_name)]
        cam = cast(Camera, actual_cam)
        cam_image = await cam.get_image(mime_type="image/jpeg")
        return cam_image
    
    async def get_detections_from_camera(
        self, camera_name: str, *, extra: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[Detection]:
        cam_image = await self.get_cam_image(camera_name)
        return await self.get_detections(cam_image, extra=extra)
    
    async def get_detections(
        self,
        image: Image.Image,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> List[Detection]:
        detections = []
        type = self.default_class
        gaze = self.gaze_detection
        if extra != None and extra.get('class') != None:
            type = extra['class']
        if extra != None and extra.get('gaze') != None:
            gaze = True
        im = viam_to_pil_image(image)
        width, height = im.size
        if gaze == True:
            result = self.model().gaze_detection.remote(im)
        else:
            result = self.model().detection.remote(im, type)

        for d in result:
            d["x_min"] = int(d["x_min"] * width)
            d["y_min"] = int(d["y_min"] * height)
            if "x_max" in d:
                d["x_max"] = int(d["x_max"] * width)
                d["y_max"] = int(d["y_max"] * height)
            
            if gaze == True:
                if not "x_max" in d:
                    d["x_max"] = d["x_min"] + 1
                    d["y_max"] = d["y_min"] + 1
            else:
                d["class_name"] = type
                d["confidence"] = 1

            detections.append(d)
        return detections
        
    async def get_classifications_from_camera(
        self,
        camera_name: str,
        count: int,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> List[Classification]:
        cam_image = await self.get_cam_image(camera_name)
        return await self.get_classifications(cam_image, count, extra=extra)
    
    async def get_classifications(
        self,
        image: ViamImage,
        count: int,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> List[Classification]:
        classifications = []
        question = self.default_question
        if extra != None and extra.get('question') != None:
            question = extra['question']
        result = self.model().classification.remote(viam_to_pil_image(image), question)
        classifications.append({"class_name": result, "confidence": 1})
        return classifications

    
    async def get_object_point_clouds(
        self, camera_name: str, *, extra: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[PointCloudObject]:
        return
    
    async def do_command(self, command: Mapping[str, ValueTypes], *, timeout: Optional[float] = None) -> Mapping[str, ValueTypes]:
        return

    async def capture_all_from_camera(
        self,
        camera_name: str,
        return_image: bool = False,
        return_classifications: bool = False,
        return_detections: bool = False,
        return_object_point_clouds: bool = False,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> CaptureAllResult:
        result = CaptureAllResult()
        result.image = await self.get_cam_image(camera_name)
        result.classifications = await self.get_classifications(result.image, 1)
        result.detections = await self.get_detections(result.image)
        return result

    async def get_properties(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> GetPropertiesResponse:
        return GetPropertiesResponse(
            classifications_supported=True,
            detections_supported=True,
            object_point_clouds_supported=False
        )