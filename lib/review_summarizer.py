import datetime
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from random import shuffle
import multiprocessing
from queue import Queue
from api_container.services_nosql import Services
from api_container.ratings_nosql import Ratings
import time

MAX_INPUT_LEN = 2**13 # 8192
HEADER_TEXT = "Customers reviews about <NAME>:\n"
MODEL = "facebook/bart-large-cnn"
MAX_WORKERS = 10
MAX_REVIEWS_TIME = 365 # days

WAIT_WORKER_TIME = 60 # seconds

#TODO: Test this class
class ReviewSummarizer:
    def __init__(self):
        self.services_manager = Services()
        self.ratings_manager = Ratings()
        self.services_queues = {}
        self.actual_workers = []

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

    def _sum_all(self, reviews):
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
    
    def _update_service(self, service_id):
        service = self.services_manager.get(service_id)
        if not service:
            return
        
        last_update = service.get('reviews_summary_updated_at', datetime.datetime.min)
        if last_update and (datetime.datetime.now() - last_update).days < 1:
            return
        
        reviews = self.ratings_manager.get_recent_by_service(MAX_REVIEWS_TIME, service_id)
        if not reviews:
            return
        
        summary = self._sum_all(reviews)
        if not summary or len(summary) == 0:
            return
        
        self.services_manager.update(service_id, {'reviews_summary': summary, 'reviews_summary_updated_at': datetime.datetime.now()})
    
    def _attempt_to_process_services(self):
        self.actual_workers = [worker for worker in self.actual_workers if worker.is_alive()]
        while len(self.actual_workers) < MAX_WORKERS:
            days_to_process = self.services_queues.keys()
            next_day_to_process = None if not days_to_process else min(days_to_process)
            if not days_to_process or (next_day_to_process - datetime.datetime.now().date()).days > 1:
                return
            queue = self.services_queues[next_day_to_process]
            next_service_id = queue.get()
            if queue.empty():
                self.services_queues.pop(next_day_to_process)
            worker = multiprocessing.Process(target=self._update_service, args=(next_service_id,))
            worker.start()
            self.actual_workers.append(worker)

    def add_service(self, service_id):
        tomorrow_date = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        if not self.services_queues.get(tomorrow_date):
            self.services_queues[tomorrow_date] = Queue()
        self.services_queues[tomorrow_date].put(service_id)
        self._attempt_to_process_services()