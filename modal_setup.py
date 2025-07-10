import modal
#from modal import Image
from pathlib import Path
from PIL import Image
import base64
import io
import os

MODEL = "vikhyatk/moondream2"
MODEL_DIR = "/root/cache"
GPU_TYPE = os.environ.get("MODAL_GPU_TYPE", "L4")  # Read from env var, default to L4

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

def encode_image_to_base64(image_path):
    """Convert an image file to base64 string"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def pil_to_base64(pil_img):
    """Convert PIL Image to base64 string"""
    # Make sure it's RGB
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

@app.cls(min_containers=0, gpu=GPU_TYPE, image=image, volumes={MODEL_DIR: vol})
@modal.concurrent(max_inputs=100)
class Moondream:
    @modal.enter()
    def start(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from PIL import Image

        print(f"Using GPU type: {GPU_TYPE}")
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL,
            cache_dir=MODEL_DIR,
            trust_remote_code=True,
            revision="2025-06-21",
            device_map={"": "cuda"}
        )


    @modal.method()
    def classification(self, base64_image=None, question: str = None):
        import time
        from PIL import Image
        import io
        import base64
        
        start = time.time()
        
        # Create a PIL Image from base64 string
        img_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(img_data))
        
        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        print(f"Classification: Image size: {image.size}, mode: {image.mode}")
        
        response = self.model.query(image, question)
        end = time.time()
        print(f"Classification time: {end - start:.2f}s")

        return response["answer"]
    
    @modal.method()
    def detection(self, base64_image=None, class_name: str = None):
        import time
        from PIL import Image
        import io
        import base64
        
        start = time.time()
        
        # Create a PIL Image from base64 string
        img_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(img_data))
        
        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        print(f"Detection: Image size: {image.size}, mode: {image.mode}")
        
        response = self.model.detect(image, class_name)
        end = time.time()
        print(f"Detection time: {end - start:.2f}s")
        
        return response["objects"]
    
    @modal.method()
    def gaze_detection(self, base64_image=None):
        import time
        from PIL import Image
        import io
        import base64
        
        start = time.time()
        
        # Create a PIL Image from base64 string
        img_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(img_data))
        
        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        print(f"Gaze Detection: Image size: {image.size}, mode: {image.mode}")
        
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
        print(f"Gaze detection time: {end - start:.2f}s")
        
        return detections
      
@app.local_entrypoint()
def main(img_path=None, question=None):
    model = Moondream()
    
    print(f"Using GPU type: {GPU_TYPE}")
    
    # Default image if none provided
    if not img_path:
        img_path = 'cat_on_counter.jpg'
    
    # Convert image to base64
    img_b64 = encode_image_to_base64(img_path)
    
    # Test classification
    response = model.classification.remote(
        img_b64, 
        question=question or "Is there a cat on a table or countertop? Answer with either yes or no."
    )
    print(f"Classification result: {response}")
    
    # Test detection
    objects = model.detection.remote(img_b64, class_name="cat")
    print(f"Detection result: {objects}")
    
    return response
