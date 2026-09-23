import logging
from functools import lru_cache

from langdetect import DetectorFactory, detect
from transformers import (
    BartForConditionalGeneration,
    BartTokenizer,
    MarianMTModel,
    MarianTokenizer,
)

DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

SUMMARY_MODEL = "facebook/bart-large-cnn"
TRANSLATION_MODEL = "Helsinki-NLP/opus-mt-mul-en"


@lru_cache(maxsize=1)
def _summary_components() -> tuple[BartForConditionalGeneration, BartTokenizer]:
    return (
        BartForConditionalGeneration.from_pretrained(SUMMARY_MODEL),
        BartTokenizer.from_pretrained(SUMMARY_MODEL),
    )


@lru_cache(maxsize=1)
def _translation_components() -> tuple[MarianMTModel, MarianTokenizer]:
    return (
        MarianMTModel.from_pretrained(TRANSLATION_MODEL),
        MarianTokenizer.from_pretrained(TRANSLATION_MODEL),
    )


def summarize(text: str) -> str:
    """Translate non-English text to English and create a BART summary."""
    try:
        language = detect(text)
        logger.info("Detected language: %s", language)

        if language != "en":
            translation_model, translation_tokenizer = _translation_components()
            translation_input = translation_tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            translated = translation_model.generate(**translation_input)
            text = translation_tokenizer.decode(translated[0], skip_special_tokens=True)

        model, tokenizer = _summary_components()
        inputs = tokenizer.encode(
            "summarize: " + text,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )
        outputs = model.generate(
            inputs,
            max_length=700,
            min_length=200,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True,
        )
        return tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
    except Exception:
        logger.exception("Error in text summarization")
        return "An error occurred during the summarization process."
