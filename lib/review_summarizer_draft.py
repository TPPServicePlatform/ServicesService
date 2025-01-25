reviews = [ "I appreciate them keeping the line outside so it’s not overcrowded inside but it seems ridiculous when it’s raining outside. When we got in we were told there were no seats so the only option was take out. My waffle was average at best and not worth the long wait. Staff were generally not pleasant and do not make you feel welcome. The Nutella theme seemed pretty underwhelming to me once we got inside.\nNot a place I’ll go a second time even if it was free.",
            "It was neat to go, but I wouldn't wait in line for 40 minutes again.\nThey seem to keep the line outside so the interior doesn't get overwhelmed. Which sucks when it's raining or cold, but I did appreciate not being totally crowded once we finally got in.\nYou order at the counter, they give you a number, then bring the food out. The numbers don't come with a stand so try to hold up your number so the servers don't walk past you.",
            "Aside from the service leaving a lot to be desired, I will definitely be back! I was expecting cloyingly sweet but everything was very well balanced. The fruit was perfect. Just the right amount of Nutella. The actual food looked better than the displays, that never happens. I'm already craving it again!",
            "The Nutella Bar in downtown Chicago is a must-visit for anyone with a sweet tooth! The atmosphere is cozy and inviting, and the menu is packed with indulgent treats that celebrate the magic of Nutella. From crepes to waffles to pastries, everything I tried was absolutely delicious and beautifully presented.\nI ordered a coffee to pair with my dessert, and while the flavor was great, I do wish it had been served a bit hotter. That said, it didn’t take away from the overall experience, which was delightful.\nIf you’re in Chicago and looking for a unique spot to enjoy some decadent desserts, the Nutella Bar is definitely worth a visit. I’ll be back for more!",
            "A one-time go-to place for desserts - I recommend trying out their nutella waffles and croissants. I was not a huge fan of their creme brulee. Wait time was around 40 minutes on Saturday evening outside (you can't enter if there are no open tables, regardless of weather), so be prepared to spend ~1.5 hours for your visit."]

# Use a pipeline as a high-level helper
from transformers import pipeline
from random import shuffle

print("Loading model...")
# pipe = pipeline("text2text-generation", model="mehassan/text_summarization-finetuned-multi-news")
# print("Model loaded.")

def get_inputs(reviews):
    print("Preparing inputs...")
    data = []
    data.extend(reviews)
    data.extend(reviews)
    data.extend(reviews)
    shuffle(reviews)
    text = "Customers reviews about a Nutella bar:\n"
    inputs = []
    working_input = text
    MAX_LEN = 8192
    for i in range(len(reviews)):
        if len(working_input) >= MAX_LEN:
            inputs.append(working_input)
            working_input = text
        review = reviews[i].replace('\\n', '  ')
        working_input += f"{review}\n"
    if len(working_input) > len(text):
        inputs.append(working_input)
    print(f"Inputs done ({len(inputs)})")
    return inputs

# summary = pipe(text, max_length=300, min_length=50, do_sample=False)
from transformers import T5Tokenizer, T5ForConditionalGeneration, BartTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer, TFT5ForConditionalGeneration

my_model = "anegi/autonlp-dialogue-summariztion-583416409"
my_model = 'hyesunyun/update-summarization-bart-large-longformer'
my_model = "facebook/bart-large-cnn"
tokenizer = AutoTokenizer.from_pretrained(my_model)
model = AutoModelForSeq2SeqLM.from_pretrained(my_model)
print("Model loaded.")
def summarize(text, max_length=150, min_length=50):
  print("sum started")
  input_ids = tokenizer.encode(text, return_tensors="pt", add_special_tokens=True)

  generated_ids = model.generate(input_ids=input_ids, num_beams=2, max_length=max_length, min_length=min_length, repetition_penalty=2.5, length_penalty=0.5, early_stopping=True)

  preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]
  print("sum done")

  return preds[0]

def sum_all(reviews):
    inputs = get_inputs(reviews)
    sums = []
    for inp in inputs:
        sum = summarize(inp, max_length=600, min_length=180)
        sums.append(sum)
    if len(sums) > 1:
        return sum_all(sums)
    return sums[0]

sumsum = sum_all(reviews)
print("\nSummary:\n")
print(sumsum)
print("\n\n\n\n\n\n")