'use client'
import { useState } from 'react';
import axios from 'axios';

interface Message {
  sender: 'User' | 'AI';
  text: string;
  timestamp: string;
  images?: string[];
  recommendedPrompts?: string[];
  recommendedUrls?: Array<{
    url: string;
    type: string;
    branch_locations?: Array<{
      branch_name: string;
      coordinates: [number, number];
      address: string;
      map_url: string;
    }>;
  }>;
  rawResponse?: any;
}

interface Service {
  id: string;
  name: string;
  endpoint: string;
  description: string;
  emoji: string;
}

const services: Service[] = [
  {
    id: 'jib_ai',
    name: 'JibAI (Sonnet 4)',
    endpoint: '/jib_ai/chat',
    description: 'Main health package assistant with RAG',
    emoji: '🧠'
  },
  {
    id: 'dr_jib',
    name: 'Dr Jib (Medical)',
    endpoint: '/dr_jib/chat',
    description: 'Medical chatbot specialist',
    emoji: '👨‍⚕️'
  },
  {
    id: 'web_agent',
    name: 'Web Agent (Intelligence)',
    endpoint: '/web_agent/chat',
    description: 'Web intelligence and package search',
    emoji: '🕸️'
  },
  {
    id: 'co_pilot',
    name: 'Co-pilot (Assistant)',
    endpoint: '/co_pilot/',
    description: 'General assistant and co-pilot',
    emoji: '🤖'
  },
  {
    id: 'ads_handler',
    name: 'Ads Handler (Contextual)',
    endpoint: '/ads_handler/chat',
    description: 'Contextual advertisement recommendations',
    emoji: '🎯'
  },
  {
    id: 'summarization',
    name: 'Summarization (Slack)',
    endpoint: '/summarization/slack',
    description: 'URL summarization service',
    emoji: '📝'
  }
];

const Chat: React.FC = () => {
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [textQuery, setTextQuery] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // Ads Handler specific state
  const [threadName, setThreadName] = useState<string>('');
  const [conversationText, setConversationText] = useState<string>('');

  const handleServiceSelect = (service: Service) => {
    setSelectedService(service);
    setMessages([]);
    setTextQuery('');
    // Clear ads handler specific state
    setThreadName('');
    setConversationText('');
  };

  const goBackToMenu = () => {
    setSelectedService(null);
    setMessages([]);
    setTextQuery('');
    // Clear ads handler specific state
    setThreadName('');
    setConversationText('');
  };

  const formatMessageForAPI = (text: string, service: Service) => {
    const timestamp = Date.now().toString();
    
    switch (service.id) {
      case 'jib_ai':
      case 'dr_jib':
      case 'web_agent':
        return {
      messages: [
            ...messages.map(msg => ({
          role: msg.sender === 'User' ? 'user' : 'assistant',
              content: msg.text
            })),
            {
              role: 'user',
              content: text
            }
          ],
          room_id: "123456"
        };
      
      case 'co_pilot':
            return {
          messages: [
            ...messages.map(msg => ({
              role: msg.sender === 'User' ? 'user' : 'assistant',
              content: msg.text
            })),
            {
              role: 'user',
              content: text
            }
          ]
        };
      
      case 'ads_handler':
        return {
          thread_name: `chat_${timestamp}`,
          conversation: [
            ...messages.map(msg => ({
              role: msg.sender === 'User' ? 'user' : 'assistant',
              content: msg.text
            })),
            {
              role: 'user',
              content: text
            }
          ]
        };
      
      case 'summarization':
            return {
          event: {
            type: 'app_mention',
            text: text,
            user: 'test_user',
            channel: 'test_channel',
            ts: timestamp
          }
        };
      
      default:
        return { message: text };
    }
  };

  const parseServiceResponse = (responseData: any, service: Service): { text: string; images?: string[]; recommendedPrompts?: string[]; recommendedUrls?: any[]; rawResponse?: any } => {
    switch (service.id) {
      case 'web_agent':
        // Web agent returns: {response, recommended_prompts_for_users, recommended_urls}
        return {
          text: responseData.response || 'No response received',
          recommendedPrompts: responseData.recommended_prompts_for_users || [],
          recommendedUrls: responseData.recommended_urls || [],
          rawResponse: responseData
        };
      
      case 'jib_ai':
      case 'dr_jib':
        // JibAI/Dr Jib returns: {text, image} or just string
        if (typeof responseData === 'string') {
          return { text: responseData };
        }
        return {
          text: responseData.text || responseData || 'No response received',
          images: responseData.image || [],
          rawResponse: responseData
        };
      
      case 'co_pilot':
        // Co-pilot returns: {response}
        return {
          text: responseData.response || responseData || 'No response received',
          rawResponse: responseData
        };
      
      case 'ads_handler':
        // Ads handler returns: Array of products directly
        const ads = Array.isArray(responseData) ? responseData : [];
        const adsText = ads.length > 0 
          ? `🎯 Found ${ads.length} contextual ads:\n\n` +
            ads.map((ad: any, index: number) => 
              `${index + 1}. ${ad.product_name}\n   💰 ฿${ad.product_cash_price?.toLocaleString() || 'N/A'}\n   🔗 ${ad.product_url}\n`
            ).join('\n')
          : `🎯 No contextual ads found`;
        
        // Extract product images for display
        const productImages = ads
          .filter((ad: any) => ad.product_image_url)
          .map((ad: any) => ad.product_image_url);
        
        return {
          text: adsText,
          images: productImages.length > 0 ? productImages : undefined,
          rawResponse: responseData
        };
      
      case 'summarization':
        // Summarization returns: {message}
        return {
          text: responseData.message || 'Processing complete!',
          rawResponse: responseData
        };
      
      default:
        // Fallback for unknown services
        if (typeof responseData === 'string') {
          return { text: responseData };
        } else if (responseData.text) {
          return { text: responseData.text, rawResponse: responseData };
        } else if (responseData.response) {
          return { text: responseData.response, rawResponse: responseData };
        } else {
          return { text: JSON.stringify(responseData, null, 2), rawResponse: responseData };
        }
    }
  };

  const sendMessage = async () => {
    if (!textQuery.trim() || !selectedService || isLoading) return;

    const userMessage: Message = {
      sender: 'User',
      text: textQuery,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const payload = formatMessageForAPI(textQuery, selectedService);
      const response = await axios.post(`http://127.0.0.1:8000${selectedService.endpoint}`, payload);
      
      // Parse response based on service type
      const parsedResponse = parseServiceResponse(response.data, selectedService);
      
      const botMessage: Message = {
        sender: 'AI',
        text: parsedResponse.text,
        timestamp: new Date().toLocaleTimeString(),
        images: parsedResponse.images,
        recommendedPrompts: parsedResponse.recommendedPrompts,
        recommendedUrls: parsedResponse.recommendedUrls,
        rawResponse: parsedResponse.rawResponse
      };

      setMessages(prev => [...prev, botMessage]);
      setTextQuery('');
    } catch (error) {
      console.error('Error sending message', error);
      const errorMessage: Message = {
        sender: 'AI',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  const parseConversationText = (text: string): Array<{role: string, content: string}> => {
    const lines = text.trim().split('\n');
    const conversation: Array<{role: string, content: string}> = [];
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue;
      
      if (trimmedLine.startsWith('User:')) {
        conversation.push({
          role: 'user',
          content: trimmedLine.replace('User:', '').trim()
        });
      } else if (trimmedLine.startsWith('Assistant:')) {
        conversation.push({
          role: 'assistant',
          content: trimmedLine.replace('Assistant:', '').trim()
        });
      }
    }
    
    return conversation;
  };

  const generateAdsFromConversation = async () => {
    if (!threadName.trim() || !conversationText.trim() || isLoading) return;

    const userMessage: Message = {
      sender: 'User',
      text: `Thread: ${threadName}\n\nConversation:\n${conversationText}`,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Parse the natural conversation text to JSON format
      const parsedConversation = parseConversationText(conversationText);
      
      const payload = {
        thread_name: threadName,
        conversation: parsedConversation
      };

      const response = await axios.post(`http://127.0.0.1:8000/ads_handler/chat`, payload);
      
      // Parse response
      const parsedResponse = parseServiceResponse(response.data, { id: 'ads_handler' } as Service);
      
      const botMessage: Message = {
        sender: 'AI',
        text: parsedResponse.text,
        timestamp: new Date().toLocaleTimeString(),
        rawResponse: parsedResponse.rawResponse
      };

      setMessages(prev => [...prev, botMessage]);
      
      // Clear the form
      setThreadName('');
      setConversationText('');
    } catch (error) {
      console.error('Error generating ads', error);
      const errorMessage: Message = {
        sender: 'AI',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecommendedPromptClick = async (prompt: string) => {
    if (isLoading) return;
    
    setTextQuery(prompt);
    
    // Auto-send the recommended prompt
    const userMessage: Message = {
      sender: 'User',
      text: prompt,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const payload = formatMessageForAPI(prompt, selectedService!);
      const response = await axios.post(`http://127.0.0.1:8000${selectedService!.endpoint}`, payload);
      
      const parsedResponse = parseServiceResponse(response.data, selectedService!);
      
      const botMessage: Message = {
        sender: 'AI',
        text: parsedResponse.text,
        timestamp: new Date().toLocaleTimeString(),
        images: parsedResponse.images,
        recommendedPrompts: parsedResponse.recommendedPrompts,
        recommendedUrls: parsedResponse.recommendedUrls,
        rawResponse: parsedResponse.rawResponse
      };

      setMessages(prev => [...prev, botMessage]);
      setTextQuery('');
    } catch (error) {
      console.error('Error sending recommended prompt', error);
      const errorMessage: Message = {
        sender: 'AI',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Service Selection Screen
  if (!selectedService) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">🧠 Jib's Brain Testing Hub</h1>
            <p className="text-lg text-gray-600">Select an AI service to test</p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((service) => (
              <div
                key={service.id}
                onClick={() => handleServiceSelect(service)}
                className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:scale-105 p-6 border-2 border-transparent hover:border-blue-200"
              >
                <div className="text-center">
                  <div className="text-4xl mb-4">{service.emoji}</div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-2">{service.name}</h3>
                  <p className="text-gray-600 text-sm mb-4">{service.description}</p>
                  <div className="bg-gray-100 rounded-lg px-3 py-1 text-xs text-gray-500 font-mono">
                    {service.endpoint}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-8 text-center">
            <div className="bg-white rounded-lg shadow-md p-4 inline-block">
              <p className="text-sm text-gray-600">
                💡 <strong>Tip:</strong> Each service has different capabilities and response formats
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Special UI for Ads Handler
  if (selectedService.id === 'ads_handler') {
    return (
      <div className="flex flex-col h-screen bg-white">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-600 to-red-600 text-white p-4 shadow-lg">
          <div className="flex items-center justify-between">
            <button
              onClick={goBackToMenu}
              className="flex items-center space-x-2 bg-white/20 hover:bg-white/30 px-3 py-2 rounded-lg transition-colors"
            >
              <span>←</span>
              <span>Back to Menu</span>
            </button>
            
            <div className="text-center">
              <h1 className="text-xl font-bold">
                🎯 Ads Handler - Custom Testing UI
              </h1>
              <p className="text-sm opacity-90">Generate contextual ads from conversation threads</p>
              <p className="text-xs opacity-75 mt-1">
                💡 Enter thread name & conversation - JSON conversion handled automatically
              </p>
            </div>
            
            <button 
              onClick={() => setMessages([])}
              className="bg-white/20 hover:bg-white/30 px-3 py-2 rounded-lg transition-colors"
            >
              🗑️ Clear
            </button>
          </div>
        </div>

        {/* Custom Ads Handler Input */}
        <div className="flex-1 p-6 bg-gray-50 overflow-y-auto">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Thread Name Input */}
            <div className="bg-white rounded-lg shadow-sm p-4 border">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🏷️ Thread Name
              </label>
              <input
                type="text"
                value={threadName}
                onChange={(e) => setThreadName(e.target.value)}
                placeholder="e.g., health_checkup_bangkok_2024"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                💡 Give your conversation thread a descriptive name
              </p>
            </div>

            {/* Conversation Input */}
            <div className="bg-white rounded-lg shadow-sm p-4 border">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💬 Conversation (Natural Format)
              </label>
              <textarea
                value={conversationText}
                onChange={(e) => setConversationText(e.target.value)}
                placeholder={`Enter conversation naturally, like this:

User: I need a health checkup in Bangkok
Assistant: What type of checkup are you looking for?
User: Full body checkup, budget around 5000 baht
Assistant: I can help you find packages in that range
User: Show me options near BTS stations`}
                className="w-full h-64 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent font-mono text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                💡 Type conversation naturally - we'll convert it to JSON format automatically
              </p>
            </div>

            {/* Generate Ads Button */}
            <div className="text-center">
              <button
                onClick={generateAdsFromConversation}
                disabled={!threadName.trim() || !conversationText.trim() || isLoading}
                className="bg-orange-600 hover:bg-orange-700 text-white px-8 py-3 rounded-lg font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isLoading ? '🔄 Generating Ads...' : '🎯 Generate Contextual Ads'}
              </button>
            </div>

            {/* Results */}
            {messages.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-4 border">
                <h3 className="font-medium text-gray-700 mb-3">🎯 Generated Ads:</h3>
                <div className="space-y-3">
                  {messages.map((msg, idx) => (
                    <div key={idx} className={`p-3 rounded-lg ${msg.sender === 'User' ? 'bg-blue-50 border-l-4 border-blue-400' : 'bg-gray-50 border-l-4 border-orange-400'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm text-gray-600">
                          {msg.sender === 'User' ? '📤 Request' : '🎯 Ads Result'}
                        </span>
                        <span className="text-xs text-gray-500">{msg.timestamp}</span>
                      </div>
                      <div className="whitespace-pre-wrap text-sm mb-3">{msg.text}</div>
                      
                      {/* Product Images */}
                      {msg.images && msg.images.length > 0 && (
                        <div className="mt-3">
                          <div className="text-sm font-medium mb-2 text-gray-600">📸 Product Images:</div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {msg.images.map((imageUrl, imgIdx) => (
                              <div key={imgIdx} className="bg-white rounded-lg border overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                                <img 
                                  src={imageUrl} 
                                  alt={`Product ${imgIdx + 1}`}
                                  className="w-full h-32 object-cover"
                                  loading="lazy"
                                />
                                <div className="p-2">
                                  <p className="text-xs text-gray-500">Product {imgIdx + 1}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Debug info */}
                      {msg.rawResponse && (
                        <details className="mt-3">
                          <summary className="text-xs text-gray-500 cursor-pointer">🔍 Debug: API Response</summary>
                          <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-auto max-h-40">
                            {JSON.stringify(msg.rawResponse, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Chat Interface Screen
  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 shadow-lg">
        <div className="flex items-center justify-between">
          <button
            onClick={goBackToMenu}
            className="flex items-center space-x-2 bg-white/20 hover:bg-white/30 px-3 py-2 rounded-lg transition-colors"
          >
            <span>←</span>
            <span>Back to Menu</span>
          </button>
          
          <div className="text-center">
            <h1 className="text-xl font-bold">
              {selectedService.emoji} {selectedService.name}
            </h1>
            <p className="text-sm opacity-90">{selectedService.description}</p>
            <p className="text-xs opacity-75 mt-1">
              {selectedService.id === 'web_agent' && '💡 Recommendations & 🔗 Links'}
              {selectedService.id === 'jib_ai' && '📸 Images & 📝 Text'}
              {selectedService.id === 'dr_jib' && '🏥 Medical & 📸 Images'}
              {selectedService.id === 'co_pilot' && '🤖 Assistant & 💬 Chat'}
              {selectedService.id === 'summarization' && '📝 Summaries & 📊 Analysis'}
              {selectedService.id === 'ads_handler' && '🎯 Contextual Ads & 💬 Thread Based'}
            </p>
          </div>
          
        <button 
          onClick={() => setMessages([])}
            className="bg-white/20 hover:bg-white/30 px-3 py-2 rounded-lg transition-colors"
        >
          🗑️ Clear
        </button>
      </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <div className="text-6xl mb-4">{selectedService.emoji}</div>
            <p>Start a conversation with {selectedService.name}</p>
            <p className="text-sm mt-2">Try asking something relevant to this service!</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.sender === 'User' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-4 rounded-lg shadow-sm ${
                msg.sender === 'User'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-800 border'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">
                  {msg.sender === 'User' ? 'You' : selectedService.name}
                </span>
                <span className="text-xs opacity-70">{msg.timestamp}</span>
              </div>
              
              {/* Main message text */}
              <div className="whitespace-pre-wrap mb-2">{msg.text}</div>
              
              {/* Images (for JibAI/Dr Jib) */}
              {msg.images && msg.images.length > 0 && (
                <div className="mt-3">
                  <div className="text-sm font-medium mb-2 text-gray-600">📸 Images:</div>
                  <div className="grid grid-cols-2 gap-2">
                      {msg.images.map((imageUrl, imgIdx) => (
                          <img 
                        key={imgIdx}
                            src={imageUrl} 
                        alt={`Response image ${imgIdx + 1}`}
                        className="rounded-lg max-w-full h-auto border"
                        loading="lazy"
                      />
                      ))}
                    </div>
                  </div>
                )}
              
              {/* Recommended Prompts (for Web Agent) */}
              {msg.recommendedPrompts && msg.recommendedPrompts.length > 0 && (
                <div className="mt-3">
                  <div className="text-sm font-medium mb-2 text-gray-600">💡 Try asking:</div>
                  <div className="flex flex-wrap gap-2">
                    {msg.recommendedPrompts.map((prompt, promptIdx) => (
                      <button
                        key={promptIdx}
                        onClick={() => handleRecommendedPromptClick(prompt)}
                        disabled={isLoading}
                        className="bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full border border-blue-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Recommended URLs (for Web Agent) */}
              {msg.recommendedUrls && msg.recommendedUrls.length > 0 && (
                <div className="mt-3">
                  <div className="text-sm font-medium mb-2 text-gray-600">🔗 Related packages:</div>
                  <div className="space-y-2">
                    {msg.recommendedUrls.map((urlInfo, urlIdx) => (
                      <div key={urlIdx} className="bg-gray-50 p-3 rounded-lg border">
                        <div className="flex items-center justify-between mb-1">
                          <a
                            href={urlInfo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium underline"
                          >
                            View Package →
                          </a>
                          <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                            {urlInfo.type}
                          </span>
                        </div>
                        {urlInfo.branch_locations && urlInfo.branch_locations.length > 0 && (
                          <div className="text-xs text-gray-600 mt-1">
                            📍 {urlInfo.branch_locations[0].branch_name}
                            {urlInfo.branch_locations.length > 1 && ` (+${urlInfo.branch_locations.length - 1} more)`}
                          </div>
            )}
          </div>
        ))}
      </div>
            </div>
          )}
              
              {/* Debug info - show raw response in development */}
              {process.env.NODE_ENV === 'development' && msg.rawResponse && (
                <details className="mt-3">
                  <summary className="text-xs text-gray-500 cursor-pointer">🔍 Debug: Raw Response</summary>
                  <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-auto">
                    {JSON.stringify(msg.rawResponse, null, 2)}
                  </pre>
                </details>
              )}
            </div>
                </div>
              ))}
              
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 border p-4 rounded-lg shadow-sm max-w-[70%]">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span>AI is thinking...</span>
                </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t bg-white p-4">
        <div className="flex space-x-3">
            <input
              type="text"
              value={textQuery}
              onChange={(e) => setTextQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={`Type your message to ${selectedService.name}...`}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            <button 
              onClick={sendMessage} 
            disabled={!textQuery.trim() || isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
            {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
        
        <div className="mt-2 text-xs text-gray-500 text-center">
          Endpoint: <code className="bg-gray-100 px-2 py-1 rounded">{selectedService.endpoint}</code>
        </div>
      </div>
    </div>
  );
};

export default Chat;
