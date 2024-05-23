import modal
from modal import Image
from pathlib import Path
from PIL import Image
import base64
import io

image = modal.Image.from_registry(
    "nvidia/cuda:12.2.0-devel-ubuntu22.04", add_python="3.12"
).apt_install(
    'pip', 'wget'
).pip_install(
 "pillow"
).run_commands([
    'nvcc --version',
    'pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122',
    'wget https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream2-text-model-f16.gguf',
    'wget https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream2-mmproj-f16.gguf'
])
app = modal.App("moondream")

def image_to_base64_data_uri(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return 'data:image/jpeg;base64,' + base64.b64encode(buffered.getvalue()).decode("utf-8")
    
@app.cls(allow_concurrent_inputs=100, keep_warm=0, gpu="A10G", image=image)
class Moondream:
    @modal.enter()
    def start(self):
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import MoondreamChatHandler

        chat_handler = MoondreamChatHandler(clip_model_path="/moondream2-mmproj-f16.gguf")


        self.llm = Llama(
            model_path="/moondream2-text-model-f16.gguf",
            filename="*text-model*",
            chat_handler=chat_handler,
            n_ctx=2048, # n_ctx should be increased to accommodate the image embedding
        )

    @modal.method()
    def completion(self, image: Image = None, question: str = None):
        import time
        start = time.time()
        response = self.llm.create_chat_completion(
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type" : "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_to_base64_data_uri(image) } }

                    ]
                }
            ]
        )
        end = time.time()
        print(end - start)

        return response["choices"][0]["message"]["content"]
    
@app.local_entrypoint()
def main(img=None, question=None, twice=True):
    model = Moondream()
    img = Image.open(
        'cat_on_counter.jpg'
    )
    response = model.completion.remote(img, question="Is there a cat on a table or countertop? Answer with either yes or no.")
    print(response)
