# Classifier Upgrade Path

When scaling RelationshipAI beyond the first 20 pilot users, the safety pre-screen system should be upgraded from the free MVP approach to dedicated hosted classifiers.

## Layer 1: Rule-Based Classifier to DistilBERT
- **MVP Approach**: Python regex and keyword list checks running in-process (<5ms).
- **Scale Upgrade**: Replace with a fine-tuned DistilBERT model hosted on Hugging Face Inference Endpoints (~$30/month).
- **Integration**: The `screen_layer1` interface remains identical; we simply swap the regex execution with an HTTP POST request to the inference endpoint.

## Layer 2: pgvector to Dedicated Pinecone Store
- **MVP Approach**: supabse pgvector cosine similarity search or mock vector search.
- **Scale Upgrade**: Replace with a dedicated safety signal vector store using Pinecone (starting with free tier, upgrading to paid at scale).
- **Integration**: Keep the same `screen_layer2` interface, updating the DB query to execute a Pinecone search query instead of a PostgreSQL cosine similarity function.
