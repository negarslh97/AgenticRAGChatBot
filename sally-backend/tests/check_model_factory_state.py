#!/usr/bin/env python3
"""
Debug script to check the current state of model_factory
and ensure it has the correct models registered.
"""

import sys
import os
import logging

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from infrastructure.model_factory import model_factory, ModelConfig, ModelProvider, ModelType
from core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_model_factory_state():
    """Check the current state of the global model factory."""
    
    logger.info("🔍 Checking model factory state...")
    
    # Check if model_factory exists
    logger.info(f"Model factory instance: {model_factory}")
    logger.info(f"Type: {type(model_factory)}")
    
    # List available models
    available_models = model_factory.list_models()
    logger.info(f"Available models: {len(available_models)}")
    
    for i, model in enumerate(available_models):
        logger.info(f"  {i+1}. {model['name']} (Provider: {model['provider']}, Type: {model['type']})")
    
    # Check if specific models are available
    target_models = [
        "minimax/minimax-m2:free",
        "google/gemini-2.5-flash",
        "moonshotai/kimi-linear-48b-a3b-instruct"
    ]
    
    for model_name in target_models:
        found = any(model['name'] == model_name for model in available_models)
        logger.info(f"Model '{model_name}': {'✅ Found' if found else '❌ Not found'}")
    
    # Check settings
    logger.info("\n🔧 Settings check:")
    logger.info(f"  chat_model_loaded: {settings.chat_model_loaded}")
    logger.info(f"  rag_model_loaded: {settings.rag_model_loaded}")
    logger.info(f"  metadata_model_loaded: {settings.metadata_model_loaded}")
    logger.info(f"  openai_api_key_loaded: {settings.openai_api_key_loaded[:10] + '...' if settings.openai_api_key_loaded else 'None'}")
    logger.info(f"  openai_base_url_loaded: {settings.openai_base_url_loaded}")
    
    return available_models

def add_missing_models():
    """Add any missing models that might be needed."""
    
    logger.info("\n🔧 Adding missing models if needed...")
    
    # Check if we need to add the minimax model
    available_models = model_factory.list_models()
    has_minimax = any(model['name'] == "minimax/minimax-m2:free" for model in available_models)
    
    if not has_minimax:
        logger.info("Adding minimax/minimax-m2:free model...")
        
        minimax_config = ModelConfig(
            name="minimax/minimax-m2:free",
            provider=ModelProvider.OPENROUTER,
            model_type=ModelType.CHAT,
            max_tokens=4096,
            temperature=0.7,
            api_key=settings.openai_api_key_loaded,
            base_url=settings.openai_base_url_loaded
        )
        
        success = model_factory.add_model(minimax_config)
        if success:
            logger.info("✅ Successfully added minimax/minimax-m2:free model")
        else:
            logger.error("❌ Failed to add minimax/minimax-m2:free model")
    else:
        logger.info("✅ minimax/minimax-m2:free model already exists")
    
    # Verify models after addition
    final_models = model_factory.list_models()
    logger.info(f"\nFinal model count: {len(final_models)}")
    
    for model in final_models:
        logger.info(f"  - {model['name']} ({model['provider']})")
    
    return len(final_models)

def test_model_selection():
    """Test model selection to ensure everything works."""
    
    logger.info("\n🧪 Testing model selection...")
    
    try:
        # Test different task types
        task_types = ["chat", "rag", "completion"]
        
        for task_type in task_types:
            try:
                optimal_model = model_factory.get_optimal_model(task_type)
                logger.info(f"✅ {task_type}: {optimal_model}")
            except Exception as e:
                logger.error(f"❌ {task_type}: {e}")
    
    except Exception as e:
        logger.error(f"❌ Model selection test failed: {e}")

if __name__ == "__main__":
    try:
        # Check current state
        models = check_model_factory_state()
        
        # Add missing models if needed
        model_count = add_missing_models()
        
        # Test model selection
        test_model_selection()
        
        logger.info("\n✅ Model factory check completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Model factory check failed: {e}")
        import traceback
        traceback.print_exc()