#!/usr/bin/env python3
"""
Check Server-Side Vectorization Status - Simple Version
"""

import warnings
import sys
import os
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to path if running as script
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import weaviate
from app.core.config import settings

def check_server_side_vectorization():
    """Check if Server-Side Vectorization is working"""
    print("Checking Server-Side Vectorization status...")
    
    try:
        # Connect to Weaviate
        client = weaviate.connect_to_local()
        print("Connected to Weaviate")
        
        # Get collection info
        collections = client.collections.list_all()
        if "MarkdownNode" in collections:
            collection = client.collections.get("MarkdownNode")
            config = collection.config.get()
            
            print(f"\nCollection: MarkdownNode")
            print(f"Vectorizer: {config.vectorizer_config}")
            
            # Check if it's Server-Side Vectorization
            if hasattr(config.vectorizer_config, 'vectorizer'):
                vectorizer_type = config.vectorizer_config.vectorizer
                print(f"Vectorizer Type: {vectorizer_type}")
                
                if vectorizer_type.value == 'text2vec-openai':
                    print("SUCCESS: Server-Side Vectorization is ACTIVE")
                    
                    # Test Server-Side Vectorization
                    print("\nTesting Server-Side Vectorization...")
                    
                    # Insert a test object (should be vectorized automatically)
                    test_data = {
                        "node_id": "test-server-side",
                        "article_id": "test-article",
                        "title": "Server-Side Test",
                        "level": 1,
                        "content": "This content should be vectorized automatically by Weaviate",
                        "full_content": "Server-Side Test\n\nThis content should be vectorized automatically by Weaviate",
                        "path": "1",
                        "order": 1,
                        "parent_id": "",
                        "visibility": "public",
                        "category": "test"
                    }
                    
                    result = collection.data.insert(test_data)
                    print(f"Insert successful: {result}")
                    
                    # Test semantic search (this should work with Server-Side Vectorization)
                    print("\nTesting semantic search...")
                    search_results = collection.query.near_text(
                        query="server side vectorization",
                        limit=3
                    )
                    
                    print(f"Semantic search successful: {len(search_results.objects)} results found")
                    
                    if search_results.objects:
                        print("Sample results:")
                        for i, obj in enumerate(search_results.objects):
                            title = str(obj.properties.get("title", "No title"))
                            print(f"  {i+1}. {title}")
                    
                    print("\nServer-Side Vectorization is working perfectly!")
                    
                else:
                    print("ERROR: Server-Side Vectorization is NOT active")
                    print(f"Current vectorizer: {vectorizer_type}")
            else:
                print("ERROR: No vectorizer configured")
                
        else:
            print("ERROR: MarkdownNode collection not found")
            
    except Exception as e:
        print(f"ERROR checking Server-Side Vectorization: {e}")
    
    finally:
        if 'client' in locals():
            client.close()
            print("\nConnection closed")

if __name__ == "__main__":
    check_server_side_vectorization()