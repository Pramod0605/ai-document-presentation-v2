import sys
import os

sys.path.insert(0, os.getcwd())

print("Testing V2 Imports...")
try:
    print("1. Importing Unified Content Generator...")
    from core.unified_content_generator import call_openrouter_llm
    print("   Success.")

    print("2. Importing SmartPartitioner...")
    from core.utils.smart_partitioner import SmartPartitioner
    print("   Success.")
    
    print("3. Instantiating SmartPartitioner...")
    sp = SmartPartitioner(None)
    print("   Success.")
    
    print("4. Importing PartitionDirectorGenerator...")
    from core.partition_director_generator import PartitionDirectorGenerator
    print("   Success.")
    
    print("5. Instantiating PartitionDirectorGenerator...")
    pdg = PartitionDirectorGenerator()
    print("   Success (ALL PASSED).")
    
except Exception as e:
    import traceback
    traceback.print_exc()
