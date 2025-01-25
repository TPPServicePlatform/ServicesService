from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from random import shuffle
import multiprocessing

MAX_INPUT_LEN = 2**13 # 8192
HEADER_TEXT = "Customers reviews about <NAME>:\n"
MODEL = "facebook/bart-large-cnn"

class ReviewSummarizer:
    def _summarize(self, text, max_length=150, min_length=50):
        tokenizer = AutoTokenizer.from_pretrained(MODEL)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)

        input_ids = tokenizer.encode(text, return_tensors="pt", add_special_tokens=True)

        generated_ids = model.generate(input_ids=input_ids, num_beams=2, max_length=max_length, min_length=min_length, repetition_penalty=2.5, length_penalty=0.5, early_stopping=True)

        preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]

        return preds[0]
    
    def _prepare_inputs(self, reviews, name):
        header_text = HEADER_TEXT.replace("<NAME>", name)
        extended_reviews = reviews * 3  # Extend reviews three times
        shuffle(extended_reviews)
        
        inputs = []
        current_input = header_text
        
        for review in extended_reviews:
            review = review.replace('\\n', '  ')
            if len(current_input) + len(review) + 1 >= MAX_INPUT_LEN:
                inputs.append(current_input)
                current_input = header_text
            current_input += f"{review}\n"
        
        if len(current_input) > len(header_text):
            inputs.append(current_input)

        return inputs

    def sum_all(self, reviews):
        if len(reviews) == 0:
            return ""
        
        inputs = self._prepare_inputs(reviews)
        summaries = []

        # for inp in inputs:
        #     summary = self._summarize(inp, max_length=600, min_length=180)
        #     summaries.append(summary)
        with multiprocessing.Pool() as pool:
            summaries = pool.map(self._summarize, inputs)            

        return summaries[0] if len(summaries) == 1 else self.sum_all(summaries)