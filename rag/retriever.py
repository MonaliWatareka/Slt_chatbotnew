from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a helpful assistant for SLT (Sri Lanka Telecom).
Use ONLY the following context extracted from the document to answer the question.
If the answer is not found in the context, say "I couldn't find that information in the document."
Do not make up any numbers or facts.

Context:
{context}

Question: {question}

Answer:""",
)


def get_answer(question: str, vectorstore, model: str = "llama3.2") -> str:
    llm       = OllamaLLM(model=model, temperature=0.1)
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    return chain.invoke(question)