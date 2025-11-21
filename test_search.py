"""
Test script to verify search functionality
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from search import SearchEngine

async def test_search():
    print("Testing search...")
    results = await SearchEngine.search("Python programming")
    
    if results:
        print(f"✅ Found {len(results)} results")
        for r in results[:2]:
            print(f"  - {r['title']}")
    else:
        print("❌ No results found")

if __name__ == "__main__":
    asyncio.run(test_search())
