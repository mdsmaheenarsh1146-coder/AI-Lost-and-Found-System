import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

MODEL_NAME = "openai/clip-vit-base-patch32"

processor = CLIPProcessor.from_pretrained(MODEL_NAME)
model = CLIPModel.from_pretrained(MODEL_NAME)

model.eval()


def get_image_embedding(image_path):
    image = Image.open(image_path).convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    with torch.no_grad():
        features = model.get_image_features(**inputs)

        # Some Transformers versions return a model output object.
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output

        features = F.normalize(
            features,
            p=2,
            dim=-1
        )

    return features.squeeze(0)