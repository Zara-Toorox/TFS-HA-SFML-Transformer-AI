"""Training package — datasets, pretrain curriculum, LoRA finetune. @zara"""

from .augmentation import (
    SolarAugmentor,
    apply_flag_augmentation,
    apply_mixup,
)
from .dataset import FinetuneDataset, PretrainDataset
from .pretrain import Pretrainer

try:
    from .finetune import LoRAFineTuner
except ModuleNotFoundError:  # Optional finetune dependency may be absent on pure-pretrain hosts.
    LoRAFineTuner = None

__all__ = [
    "FinetuneDataset",
    "LoRAFineTuner",
    "PretrainDataset",
    "Pretrainer",
    "SolarAugmentor",
    "apply_flag_augmentation",
    "apply_mixup",
]
