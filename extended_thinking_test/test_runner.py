import asyncio
import sys
from sonnet4_agent import Sonnet4Agent, TEST_QUERIES

async def interactive_test():
    """Interactive test mode for individual queries"""
    print("🚀 Sonnet 4 Interactive Test Mode")
    print("="*50)
    
    agent = Sonnet4Agent()
    
    while True:
        print("\nOptions:")
        print("1. Enter custom query")
        print("2. Use predefined test queries")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            query = input("\nEnter your query: ").strip()
            if not query:
                print("Empty query, skipping...")
                continue
                
        elif choice == "2":
            print("\nPredefined test queries:")
            for i, q in enumerate(TEST_QUERIES, 1):
                print(f"{i}. {q[:60]}...")
            
            try:
                idx = int(input("Select query (1-5): ")) - 1
                if 0 <= idx < len(TEST_QUERIES):
                    query = TEST_QUERIES[idx]
                else:
                    print("Invalid selection!")
                    continue
            except ValueError:
                print("Invalid input!")
                continue
                
        elif choice == "3":
            print("Goodbye! 👋")
            break
            
        else:
            print("Invalid option!")
            continue
        
        print(f"\n{'='*60}")
        print(f"🧪 TESTING: {query}")
        print('='*60)
        
        try:
            result = await agent.chat(query)
            
            print(f"\n✅ RESPONSE:")
            print(result['response'])
            
            print(f"\n📊 METADATA:")
            print(f"Iterations: {result['iterations']}")
            print(f"Tools Used: {len(result['tools_used'])}")
            print(f"Stop Reason: {result['stop_reason']}")
            
            if result['thinking']:
                print(f"\n🧠 THINKING PROCESS:")
                print(result['thinking'][:500] + "..." if len(result['thinking']) > 500 else result['thinking'])
            
            if result['tools_used']:
                print(f"\n🔧 TOOLS USED:")
                for i, tool in enumerate(result['tools_used'], 1):
                    print(f"{i}. {tool['name']}")
                    print(f"   Input: {tool['input']}")
                    print(f"   Result: {tool['result'][:100]}...")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    asyncio.run(interactive_test()) 