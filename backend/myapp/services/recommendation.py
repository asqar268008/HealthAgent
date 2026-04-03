from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from myapp.model import get_model


def build_recommendation_chain():

    llm = get_model()

    prompt_template = """
You are a healthcare lifestyle assistant.

Convert the following clinical decision into clear lifestyle advice.

Rules:
- Use bullet points
- Maximum 6 bullets
- Simple language
- Focus on diet, exercise, sleep, stress, monitoring

Clinical Decision:
{decision_output}
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template),
            ("human", "Rewrite this decision as lifestyle advice.")
        ]
    )

    chain = prompt | llm | StrOutputParser()

    return chain


def get_recommendations(decision_output):
    try:
        chain = build_recommendation_chain()

        result = chain.invoke({
            "decision_output": decision_output
        })

        # ✅ Convert bullet string → list
        lines = result.strip().split("\n")

        clean_list = [
            line.replace("•", "").replace("-", "").strip()
            for line in lines if line.strip()
        ]

        return clean_list

    except Exception as e:
        return []