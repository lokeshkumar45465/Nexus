
from data_loader import load_dataset
from question_handler import understand_question

df = load_dataset()

test_questions = [
    "How many records are in the dataset?",
    "Tell me the number of records",
    "How many unique assets are there?",
    "What is the average health score?",
    "How many recorded failures are there?",
    "Which maintenance is due?",
    "What is the weather on my factory floor?",
]

for question in test_questions:
    answer = understand_question(question, df)
    print("\nQuestion:", question)
    print("Answer:", answer)
