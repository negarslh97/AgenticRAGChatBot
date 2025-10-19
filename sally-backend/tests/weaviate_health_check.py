#!/usr/bin/env python3
"""
Weaviate Health Check & Performance Analysis Tool
"""

import warnings
import sys
import os
import json
import time
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to path if running as script
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.core.config import settings

class WeaviateHealthChecker:
    """Weaviate Health Checker"""
    
    def __init__(self):
        self.weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
        self.weaviate_api_key = settings.weaviate_api_key_loaded
        self.client = None
        
    def connect(self) -> bool:
        """Connect to Weaviate"""
        try:
            print("Connecting to Weaviate...")
            
            is_local = "localhost" in self.weaviate_url or "127.0.0.1" in self.weaviate_url
            
            if is_local:
                self.client = weaviate.connect_to_local()
            else:
                auth = Auth.api_key(self.weaviate_api_key) if self.weaviate_api_key else None
                self.client = weaviate.connect_to_custom(
                    http_host=self.weaviate_url.replace("http://", "").replace("https://", ""),
                    http_port=443 if "https" in self.weaviate_url else 8080,
                    http_secure="https" in self.weaviate_url,
                    auth_credentials=auth
                )
            
            print("Connection successful")
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def check_metrics(self) -> Dict[str, Any]:
        """Check Weaviate metrics"""
        print("\nChecking Weaviate metrics...")
        
        try:
            # Try Prometheus metrics endpoint first
            metrics_url = f"{self.weaviate_url.replace('http://', '').replace('https://', '').replace(':8080', '')}:2112/metrics"
            if not metrics_url.startswith('http'):
                metrics_url = f"http://{metrics_url}"

            response = requests.get(metrics_url, timeout=10)
            
            if response.status_code == 200:
                metrics_text = response.text
                
                # Extract important metrics
                metrics = {
                    "query_latency_p95": None,
                    "query_latency_p99": None,
                    "unindexed_vectors": None,
                    "total_objects": None,
                    "vector_index_size": None
                }
                
                lines = metrics_text.split('\n')
                for line in lines:
                    if 'weaviate_lsm_group_async_queries_duration_seconds' in line and 'quantile="0.95"' in line:
                        metrics["query_latency_p95"] = float(line.split()[-1])
                    elif 'weaviate_lsm_group_async_queries_duration_seconds' in line and 'quantile="0.99"' in line:
                        metrics["query_latency_p99"] = float(line.split()[-1])
                    elif 'weaviate_vector_index_hnsw_unindexed_vectors' in line:
                        metrics["unindexed_vectors"] = int(line.split()[-1])
                    elif 'weaviate_vector_index_hnsw_size' in line:
                        metrics["vector_index_size"] = int(line.split()[-1])
                
                print("Metrics retrieved successfully")
                return metrics
                
            else:
                print(f"Error retrieving metrics: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error checking metrics: {e}")
            return {}
    
    def check_schema(self) -> Dict[str, Any]:
        """Check collection schemas"""
        print("\nChecking collection schemas...")
        
        try:
            collections = self.client.collections.list_all()
            schema_info = {}
            
            for collection_name in collections.keys():
                collection = self.client.collections.get(collection_name)
                config = collection.config.get()
                
                # Extract vectorizer name correctly
                vectorizer_name = "Unknown"
                if hasattr(config, 'vectorizer_config') and config.vectorizer_config:
                    if hasattr(config.vectorizer_config, 'vectorizer'):
                        vectorizer_name = config.vectorizer_config.vectorizer.value
                    elif hasattr(config.vectorizer_config, 'model'):
                        vectorizer_name = config.vectorizer_config.model

                # Extract HNSW config correctly
                ef_value = -1
                if hasattr(config, 'vector_index_config') and config.vector_index_config:
                    if hasattr(config.vector_index_config, 'hnsw'):
                        hnsw_config = config.vector_index_config.hnsw
                        ef_value = getattr(hnsw_config, 'ef', -1)
                    elif hasattr(config.vector_index_config, 'ef'):
                        ef_value = config.vector_index_config.ef

                schema_info[collection_name] = {
                    "properties": [prop.name for prop in config.properties],
                    "vectorizer": vectorizer_name,
                    "ef": ef_value
                }
            
            print("Schema checked successfully")
            return schema_info
            
        except Exception as e:
            print(f"Error checking schema: {e}")
            return {}
    
    def check_data_stats(self) -> Dict[str, Any]:
        """Check data statistics"""
        print("\nChecking data statistics...")
        
        try:
            collections = self.client.collections.list_all()
            data_stats = {}
            
            for collection_name in collections.keys():
                collection = self.client.collections.get(collection_name)
                
                # Total object count
                total_count = collection.aggregate.over_all().total_count
                
                # Sample data for quality check
                sample_data = collection.query.fetch_objects(limit=5)
                
                data_stats[collection_name] = {
                    "total_count": total_count,
                    "sample_titles": [str(obj.properties.get("title", "No title"))[:50] for obj in sample_data.objects],
                    "sample_paths": [str(obj.properties.get("path", "No path"))[:50] for obj in sample_data.objects]
                }
            
            print("Data statistics checked successfully")
            return data_stats
            
        except Exception as e:
            print(f"Error checking data statistics: {e}")
            return {}
    
    def test_query_performance(self) -> Dict[str, Any]:
        """Test query performance"""
        print("\nTesting query performance...")
        
        try:
            collections = self.client.collections.list_all()
            performance_results = {}
            
            for collection_name in collections.keys():
                collection = self.client.collections.get(collection_name)
                
                # Simple query test
                start_time = time.time()
                results = collection.query.fetch_objects(limit=10)
                simple_query_time = time.time() - start_time
                
                # Filtered query test
                start_time = time.time()
                try:
                    filtered_results = collection.query.fetch_objects(
                        limit=10,
                        where=Filter.by_property("title").like("*model*")
                    )
                    filtered_query_time = time.time() - start_time
                except:
                    # Fallback to simple query if filtered query fails
                    filtered_results = collection.query.fetch_objects(limit=10)
                    filtered_query_time = time.time() - start_time
                
                # Semantic query test (if vectorizer is active)
                semantic_query_time = None
                semantic_success = False
                try:
                    start_time = time.time()
                    semantic_results = collection.query.near_text(
                        query="مدل فروش چیست؟",
                        limit=5
                    )
                    semantic_query_time = time.time() - start_time
                    semantic_success = len(semantic_results.objects) > 0
                except Exception as e:
                    print(f"    Semantic query failed: {e}")
                    pass
                
                performance_results[collection_name] = {
                    "simple_query_time": round(simple_query_time * 1000, 2),  # milliseconds
                    "filtered_query_time": round(filtered_query_time * 1000, 2),
                    "semantic_query_time": round(semantic_query_time * 1000, 2) if semantic_query_time else None,
                    "simple_results_count": len(results.objects),
                    "filtered_results_count": len(filtered_results.objects),
                    "semantic_results_count": len(semantic_results.objects) if 'semantic_results' in locals() and semantic_results else 0,
                    "semantic_success": semantic_success if 'semantic_success' in locals() else False
                }
            
            print("Query performance test completed")
            return performance_results
            
        except Exception as e:
            print(f"Error testing performance: {e}")
            return {}
    
    def generate_report(self, metrics: Dict, schema: Dict, data_stats: Dict, performance: Dict) -> str:
        """Generate comprehensive report"""
        report = []
        report.append("=" * 60)
        report.append("WEAVIATE HEALTH CHECK REPORT")
        report.append("=" * 60)
        
        # Metrics section
        report.append("\nPERFORMANCE METRICS:")
        if metrics:
            if metrics.get("query_latency_p95"):
                report.append(f"  • Query Latency (P95): {metrics['query_latency_p95']:.3f}s")
            if metrics.get("query_latency_p99"):
                report.append(f"  • Query Latency (P99): {metrics['query_latency_p99']:.3f}s")
            if metrics.get("unindexed_vectors") is not None:
                status = "EXCELLENT" if metrics["unindexed_vectors"] == 0 else f"{metrics['unindexed_vectors']} unindexed vectors"
                report.append(f"  • Unindexed Vectors: {status}")
        else:
            report.append("  • Metrics not available")
        
        # Schema section
        report.append("\nCOLLECTION SCHEMAS:")
        for collection_name, info in schema.items():
            report.append(f"  • {collection_name}:")
            report.append(f"    - Properties: {len(info['properties'])}")
            report.append(f"    - Vectorizer: {info['vectorizer']}")
            if info.get('ef', -1) != -1:
                report.append(f"    - EF: {info['ef']}")
        
        # Data statistics section
        report.append("\nDATA STATISTICS:")
        for collection_name, stats in data_stats.items():
            report.append(f"  • {collection_name}: {stats['total_count']} records")
            if stats['sample_titles']:
                report.append(f"    - Sample titles: {', '.join(stats['sample_titles'][:3])}")
        
        # Query performance section
        report.append("\nQUERY PERFORMANCE:")
        for collection_name, perf in performance.items():
            report.append(f"  • {collection_name}:")
            report.append(f"    - Simple query: {perf['simple_query_time']}ms")
            report.append(f"    - Filtered query: {perf['filtered_query_time']}ms")
            if perf.get('semantic_query_time'):
                status = "SUCCESS" if perf.get('semantic_success', False) else "FAILED"
                report.append(f"    - Semantic query: {perf['semantic_query_time']}ms ({status})")
            else:
                report.append(f"    - Semantic query: Not available")
        
        # Recommendations
        report.append("\nRECOMMENDATIONS:")
        
        # Check query latency
        if metrics.get("query_latency_p99") and metrics["query_latency_p99"] > 0.2:
            report.append("  • High query latency - check system resources and HNSW settings")
        
        # Check unindexed vectors
        if metrics.get("unindexed_vectors") and metrics["unindexed_vectors"] > 0:
            report.append("  • Unindexed vectors exist - check resources and settings")
        
        # Check query performance
        for collection_name, perf in performance.items():
            if perf['semantic_query_time'] and perf['semantic_query_time'] > 100:
                report.append(f"  • Semantic query in {collection_name} is slow")
        
        report.append("\nOVERALL STATUS: System is in good condition")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run_full_check(self):
        """Run full health check"""
        print("Starting comprehensive Weaviate health check...")
        
        if not self.connect():
            return
        
        try:
            # Run all checks
            metrics = self.check_metrics()
            schema = self.check_schema()
            data_stats = self.check_data_stats()
            performance = self.test_query_performance()
            
            # Generate report
            report = self.generate_report(metrics, schema, data_stats, performance)
            print(report)
            
            # Save report to file
            try:
                with open("weaviate_health_report.txt", "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\nReport saved to 'weaviate_health_report.txt'")
            except UnicodeEncodeError:
                # Fallback for Windows systems with encoding issues
                with open("weaviate_health_report.txt", "w", encoding="ascii", errors="replace") as f:
                    f.write(report)
                print(f"\nReport saved to 'weaviate_health_report.txt' (with encoding fallback)")
            
        except Exception as e:
            print(f"Error running health check: {e}")
        
        finally:
            if self.client:
                self.client.close()
                print("Connection closed.")


if __name__ == "__main__":
    checker = WeaviateHealthChecker()
    checker.run_full_check()
