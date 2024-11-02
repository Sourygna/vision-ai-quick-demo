from abc import ABC, abstractmethod
import logging

import vertexai
from vertexai.preview.vision_models import Image, ImageTextModel
from vertexai.generative_models import GenerativeModel, GenerationConfig, Image as ImageGemini
from google.cloud import texttospeech
from preferredsoundplayer import *

project_id = "my-super-gcp-project"  # TODO put your own project here
location = "europe-west4"  # TODO put your favourite GCP location here

vertexai.init(project=project_id, location=location)
logging.basicConfig(format='%(message)s', level=logging.INFO)


class ImageAnalyzer(ABC):
    def __init__(self, image_file: str):
        self.image_file = image_file
        self.gemini_model = GenerativeModel("gemini-1.5-flash-002")

    @abstractmethod
    def analyze(self, question: str, language="English") -> str:
        pass


class ImageAnalyzerVision(ImageAnalyzer):
    def _basic_analyze(self, question: str):
        model = ImageTextModel.from_pretrained("imagetext@001")
        source_img = Image.load_from_file(location=self.image_file)

        answers = model.ask_question(image=source_img, question=question)

        answer = answers[0]
        logging.info(answer)

        return answer

    def _elaborate_answer(self, question: str, raw_answer: str, language: str):
        prompt = f"""Based on the following question and answer, create an answer with a full sentence.
        Make sure this answer is in {language}.
        QUESTION: {question}
        ANSWER: {raw_answer}
        """

        response = self.gemini_model.generate_content(prompt)
        logging.info(response.text)
        return response.text

    def analyze(self, question: str, language="English") -> str:
        raw_answer = self._basic_analyze(question)
        return self._elaborate_answer(question, raw_answer, language)


class ImageAnalyzerGemini(ImageAnalyzer):
    def analyze(self, question: str, language="English") -> str:
        if language == "English":
            prompt = question
        else:
            prompt = question + f". Return an answer in {language}"

        source_img = ImageGemini.load_from_file(location=self.image_file)
        response = self.gemini_model.generate_content([source_img, prompt])

        logging.info(response.text)
        return response.text

    def analyze_json_output(self):
        response_schema = {
            "type": "object",
            "properties": {
                "brand": {"type": "string", },
                "model": {"type": "string", },
                "color": {"type": "string", },
            },
            "required": ["brand", "model", "color"],
        }

        prompt = "What is the brand, the model and the color of this car ?"

        source_img = ImageGemini.load_from_file(location=self.image_file)

        response = self.gemini_model.generate_content(
            [source_img, prompt],
            generation_config=GenerationConfig(response_mime_type="application/json", response_schema=response_schema)
        )

        logging.info(response.text)


class Speaker:
    def __init__(self):
        self.text2speech_client = texttospeech.TextToSpeechClient()

    @staticmethod
    def _get_voice_config(language: str, operator: str):
        # Check https://cloud.google.com/text-to-speech/docs/voices to add more voices/languages
        config = {
            "English": {
                "Maria": {
                    "language_code": "en-US",
                    "name": "en-US-Standard-C"
                },
                "Juan": {
                    "language_code": "en-US",
                    "name": "en-US-Standard-D"
                }
            },
            "Arabic": {
                "Maria": {
                    "language_code": "ar-XA",
                    "name": "ar-XA-Standard-A"
                },
                "Juan": {
                    "language_code": "ar-XA",
                    "name": "ar-XA-Standard-B"
                }
            },
            "French": {
                "Maria": {
                    "language_code": "fr-FR",
                    "name": "fr-FR-Standard-C"
                },
                "Juan": {
                    "language_code": "fr-FR",
                    "name": "fr-FR-Standard-B"
                }
            },
            "Spanish": {
                "Maria": {
                    "language_code": "es-ES",
                    "name": "es-ES-Studio-C"
                },
                "Juan": {
                    "language_code": "es-ES",
                    "name": "es-ES-Studio-F"
                }
            }
        }

        language_code = config[language][operator]['language_code']
        name = config[language][operator]['name']
        voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=name)

        return voice

    def talk(self, text_to_read: str, language="English", operator="Maria"):
        input_text = texttospeech.SynthesisInput(
            text=text_to_read  # noqa
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3  # noqa
        )

        voice_config = self._get_voice_config(language, operator)
        response = self.text2speech_client.synthesize_speech(
            request={"input": input_text, "voice": voice_config, "audio_config": audio_config}
        )

        with open("output.mp3", "wb") as out:
            out.write(response.audio_content)

        soundplay("output.mp3")


if __name__ == '__main__':
    # language_answer = "French"
    language_answer = "English"

    my_question = "What is the plate number of this car?"
    # my_question = "In which state of the USA is this car matriculated?"

    image = "unplash-car.jpg"

    image_analyzer = ImageAnalyzerGemini(image)
    # image_analyzer = ImageAnalyzerVision(image)
    my_answer = image_analyzer.analyze(my_question, language=language_answer)

    speaker = Speaker()
    speaker.talk(my_answer, language=language_answer)

    # Other example, to enforce a JSON output:
    # image_analyzer = ImageAnalyzerGemini(image)
    # image_analyzer.analyze_json_output()
