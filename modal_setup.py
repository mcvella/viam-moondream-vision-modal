import modal
from modal import Image
from pathlib import Path
from PIL import Image
import base64
import io
import os

MODEL = "vikhyatk/moondream2"
MODEL_DIR = "/root/cache"

image = modal.Image.from_registry(
    "nvidia/cuda:12.6.0-devel-ubuntu22.04", add_python="3.12"
).apt_install(
    'pip', 'wget', 'clang'
).pip_install(
 'pillow', 'transformers', 'einops', 'pyvips', 'huggingface_hub'
).run_commands([
    'nvcc --version',
    'pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126',
    'pip install "accelerate>=0.26.0"',
    'apt install -y libvips'
]).env({"HF_HUB_CACHE": MODEL_DIR})

app = modal.App("moondream")

vol = modal.Volume.from_name("cache", create_if_missing=True)


def image_to_base64_data_uri(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return 'data:image/jpeg;base64,' + base64.b64encode(buffered.getvalue()).decode("utf-8")
    
@app.cls(allow_concurrent_inputs=100, keep_warm=0, gpu="L4", image=image, volumes={MODEL_DIR: vol})
class Moondream:
    @modal.enter()
    def start(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from PIL import Image

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL,
            cache_dir=MODEL_DIR,
            trust_remote_code=True,
            revision="2025-01-09",
            device_map={"": "cuda"}
        )


    @modal.method()
    def classification(self, image: Image = None, question: str = None):
        import time
        start = time.time()
        response = self.model.query(image, question)
        end = time.time()
        print(end - start)

        return response["answer"]
    
    @modal.method()
    def detection(self, image: Image = None, type: str = None):
        import time
        start = time.time()
        response = self.model.detect(image, type)
        end = time.time()
        print(end - start)
        return response["objects"]
    
    @modal.method()
    def gaze_detection(self, image: Image = None):
        import time
        start = time.time()
        detections = []
        response = self.model.detect(image, "face")
        print(response)
        face_index = 0
        for face in response["objects"]:
            face_center = (
                float(face["x_min"] + face["x_max"]) / 2,
                float(face["y_min"] + face["y_max"]) / 2,
            )
            gaze_result = self.model.detect_gaze(image, face_center)
            print(gaze_result)
            if (
                gaze_result["gaze"] is not None
                and isinstance(gaze_result["gaze"], dict)
                and "x" in gaze_result["gaze"]
                and "y" in gaze_result["gaze"]
            ):
                detections.append({"class_name": f"gaze_{face_index}", "confidence": 1, "x_min": gaze_result["gaze"]["x"], "y_min": gaze_result["gaze"]["y"]})
            # add face detection even if we don't find a gaze for it (above)
            face["class_name"] = f"face_{face_index}"
            face["confidence"] = 1
            detections.append(face)
            face_index = face_index + 1
        end = time.time()
        print(end - start)
        return detections
      
@app.local_entrypoint()
def main(img=None, question=None, twice=True):
    model = Moondream()
    img = Image.open(
        'cat_on_counter.jpg'
    )
    response = model.classification.remote(img, question="Is there a cat on a table or countertop? Answer with either yes or no.")
    print(response)
