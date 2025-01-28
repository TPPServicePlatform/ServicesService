from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class SentenceComparator:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL)
        self.model = AutoModel.from_pretrained(MODEL)

    #Mean Pooling - Take attention mask into account for correct averaging
    def _mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0] #First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def compare(self, main_sentence, sentences):
        sentences = [main_sentence] + sentences

        # Tokenize sentences
        encoded_input = self.tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)

        # Perform pooling
        sentence_embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])

        # Normalize embeddings
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        # Get similarity results
        results = []

        for sentence, embedding in zip(sentences, sentence_embeddings):
            distance = F.cosine_similarity(embedding.unsqueeze(0), sentence_embeddings[0].unsqueeze(0)).item()
            results.append((sentence, distance))

        return results
