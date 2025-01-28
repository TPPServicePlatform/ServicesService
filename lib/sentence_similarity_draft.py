from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# Sentences we want sentence embeddings for
sentences = ['That is a happy person', 'Today is a sunny day', 'That is a very happy person', 'That is a happy cat',
             'Today will rain', 'Thats a happy cloud', 'Tomorrow is closed', 'THere is a happy dog',
             'The school is open', 'The school is closed', 'The school is open today', 'The school is closed today',
             'The tshirt is red', 'The tshirt is blue', 'The tshirt is green', 'The tshirt is yellow',
             'Wow! No ball is red', "OMG! I'm so happy", 'I am so sad', 'I am so happy', 'I am so angry',
                'I am so tired', 'I am so excited', 'I am so bored', 'I am so scared', 'I am so surprised']

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')

# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)

# Perform pooling
sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

# Normalize embeddings
sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

# Get similarity results
results = []
compare_to = sentences[0]

for sentence, embedding in zip(sentences, sentence_embeddings):
    distance = F.cosine_similarity(embedding.unsqueeze(0), sentence_embeddings[0].unsqueeze(0)).item()
    results.append((sentence, distance))

results.sort(key=lambda x: x[1], reverse=True)

for sentence, distance in results:
    print(f'Similarity between "{sentence}" and "{compare_to}": {distance:.4f}')
