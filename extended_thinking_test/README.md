# 🧠 Sonnet 4 Extended Thinking Test Environment

This directory contains a test environment for experimenting with **Claude Sonnet 4's extended thinking capabilities** before integrating them into the main bot.

## 🎯 Purpose

- Test Sonnet 4's built-in thinking mode
- Experiment with parallel tool calling
- Understand response structures and edge cases
- Validate tool integration patterns

## 📁 Files

- `sonnet4_agent.py` - Main Sonnet 4 agent with thinking capabilities
- `test_runner.py` - Interactive test runner for individual queries  
- `README.md` - This documentation

## 🔧 Tools Available

### 1. **Calculator** 
- Mathematical operations and calculations
- Supports basic arithmetic and math functions

### 2. **Weather Check** (Dummy)
- Weather information for different cities
- Uses dummy data for testing

### 3. **SQL Search** (Dummy)
- Text-to-SQL search functionality
- Pandas query syntax testing
- Category filtering simulation

### 4. **Retrieval** (Dummy)
- Healthcare package search simulation
- Location and keyword-based filtering

## 🚀 How to Run

### Run All Test Queries
```bash
cd extended_thinking_test
python sonnet4_agent.py
```

### Interactive Testing
```bash
cd extended_thinking_test  
python test_runner.py
```

## 🧪 Test Queries

1. **Multi-tool Weather + Math**: "What's the weather like in Bangkok and calculate the average temperature if it's been 32°C, 30°C, and 35°C for the past 3 days?"

2. **SQL Search**: "Find me the cheapest HPV vaccines under 15,000 baht in Bangkok area"

3. **Complex SQL**: "I need health checkup packages under 5000 baht. Can you search for the top 5 cheapest ones?"

4. **Math + Search**: "Calculate the compound interest on 100,000 baht at 5% annual rate for 3 years, then find health packages in that price range"

5. **Parallel Tools**: "What's the weather in Chiang Mai? Also, find dental services there under 3000 baht"

## 🔍 What to Observe

### **Response Structure**
- `response` - Final AI response
- `thinking` - Built-in reasoning process
- `iterations` - Number of API calls made
- `tools_used` - List of tools called
- `stop_reason` - Why the conversation ended
- `conversation_history` - Full message history

### **Thinking Patterns**
- How Sonnet 4 reasons about tool usage
- Decision making for multiple tools
- Error handling and fallbacks

### **Tool Coordination**
- Sequential vs parallel tool usage
- Context passing between tools
- Result synthesis

## 🎯 Key Observations to Make

1. **When does Sonnet 4 use multiple tools?**
2. **How does it handle tool errors?**
3. **What's the thinking quality like?**
4. **How many iterations does it typically take?**
5. **Are there any edge cases in response structure?**

## 🔄 Next Steps

After testing, we'll integrate these patterns into:
- `bot.py` - Main Claude bot
- `tools.py` - Tool definitions  
- Enhanced thinking and parallel calling

## 💡 Tips

- Try queries that require multiple tools
- Test error scenarios (invalid calculations, etc.)
- Observe the thinking process for insights
- Note any unexpected behaviors or patterns

---

**Happy Testing!** 🚀 This will help us build an amazing Sonnet 4 integration! 