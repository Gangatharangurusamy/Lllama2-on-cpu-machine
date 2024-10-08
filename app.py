from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import CTransformers
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Load the PDF File
loader = DirectoryLoader('data/', glob="*.pdf", loader_cls=PyPDFLoader)
documents = loader.load()

# Split Text into Chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
text_chunks = text_splitter.split_documents(documents)

# Load the Embedding Model
embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2', 
                                    model_kwargs={'device': 'cpu'})

# Convert the Text Chunks into Embeddings and Create a FAISS Vector Store
vector_store = FAISS.from_documents(text_chunks, embeddings)

# Load the Language Model
llm = CTransformers(model="model/llama-2-7b-chat.ggmlv3.q4_0.bin",
                    model_type="llama",
                    config={'max_new_tokens': 128, 'temperature': 0.01})

# Define your prompt template (Make sure this is defined)
template = "Given the context: {context}, answer the question: {question}"  # Adjust as needed
qa_prompt = PromptTemplate(template=template, input_variables=['context', 'question'])


# Create the QA Chain
chain = RetrievalQA.from_chain_type(llm=llm,
                                     chain_type='stuff',
                                     retriever=vector_store.as_retriever(search_kwargs={'k': 2}),
                                     return_source_documents=False,
                                     chain_type_kwargs={'prompt': qa_prompt})

@app.route('/', methods=["GET", "POST"])
def index():
    return render_template('index.html', **locals())

@app.route('/chatbot', methods=["GET", "POST"])
def chatbotResponse():
    if request.method == 'POST':
        user_input = request.form['question']
        print(f"User Input: {user_input}")

        try:
            result = chain.invoke({'query': user_input})
            print(f"Answer: {result['result']}")
            return jsonify({"response": str(result['result']) })
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"response": "An error occurred while processing your request."})

    return jsonify({"response": "Please send a POST request."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
