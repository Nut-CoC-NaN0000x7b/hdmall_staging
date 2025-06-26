'use client'
import { useState, ChangeEvent, useRef } from 'react';
import axios from 'axios';

interface Message {
  sender: 'User' | 'Jib AI';
  text: string;
  type?: 'text' | 'image_url' | 'image_file';
  fileName?: string;
  images?: string[]; // For bot response images
}

interface LocalImageFile {
  file: File;
  base64Data: string;
  mediaType: string;
  preview: string;
}

// Function to determine if a string is a valid URL
const isValidURL = (str: string): boolean => {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
};

// Function to extract multiple URLs from textarea
const extractImageURLs = (input: string): string[] => {
  return input
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && isValidURL(line))
    .filter(url => {
      // Allow all image URLs, don't filter out hdmall.co.th
      return url.match(/\.(jpg|jpeg|png|gif|webp|bmp|svg)(\?.*)?$/i) || 
             url.includes('image') || 
             url.includes('img') ||
             !url.startsWith('https://hdmall.co.th/'); // Keep non-hdmall URLs
    });
};

// Function to convert file to base64 and detect media type
const convertFileToBase64 = (file: File): Promise<LocalImageFile> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64String = reader.result as string;
      const base64Data = base64String.split(',')[1]; // Remove data:image/type;base64, prefix
      const mediaType = file.type || 'image/jpeg'; // Default to jpeg if type not detected
      
      resolve({
        file,
        base64Data,
        mediaType,
        preview: base64String // Keep full data URL for preview
      });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

const Chat: React.FC = () => {
  const [imageUrls, setImageUrls] = useState<string>('');
  const [textQuery, setTextQuery] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [imagePreviewUrls, setImagePreviewUrls] = useState<string[]>([]);
  const [localImages, setLocalImages] = useState<LocalImageFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Update image previews when URLs change
  const handleImageUrlsChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setImageUrls(value);
    
    // Extract valid image URLs for preview
    const validUrls = extractImageURLs(value);
    setImagePreviewUrls(validUrls);
  };

  // Handle local file selection
  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    try {
      const processedFiles = await Promise.all(
        imageFiles.map(file => convertFileToBase64(file))
      );
      setLocalImages(prev => [...prev, ...processedFiles]);
    } catch (error) {
      console.error('Error processing files:', error);
    }
  };

  // Remove local image
  const removeLocalImage = (index: number) => {
    setLocalImages(prev => prev.filter((_, i) => i !== index));
  };

  // Clear all local images
  const clearLocalImages = () => {
    setLocalImages([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Function to handle sending the message to your LLM endpoint
  const sendMessage = async () => {
    const validImageUrls = extractImageURLs(imageUrls);
    const query = textQuery.trim();
    
    if (!query && validImageUrls.length === 0 && localImages.length === 0) return;

    const userMessages: any[] = [];

    // Add URL-based image messages
    validImageUrls.forEach(url => {
      userMessages.push({
        sender: 'User',
        text: url,
        type: 'image_url',
      });
    });

    // Add local file-based image messages
    localImages.forEach(localImage => {
      userMessages.push({
        sender: 'User',
        text: localImage.preview, // Use preview for display
        type: 'image_file',
        fileName: localImage.file.name,
      });
    });
    
    // Add text message if present
    if (query) {
      userMessages.push({
        sender: 'User',
        text: query,
        type: 'text',
      });
    }

    // Update the messages state with the user's message(s)
    setMessages((prev) => [...prev, ...userMessages]);

    // Prepare the complete payload including all previous messages
    const payload = {
      messages: [
        ...messages.map((msg) => ({
          role: msg.sender === 'User' ? 'user' : 'assistant',
          content: msg.type === 'image_url'
            ? [
                {
                  type: 'image',
                  source: {
                    type: 'url',
                    url: msg.text,
                  },
                },
              ]
            : msg.type === 'image_file'
            ? [
                {
                  type: 'image',
                  source: {
                    type: 'base64',
                    media_type: 'image/jpeg', // We'll need to store this properly
                    data: msg.text.split(',')[1], // Extract base64 data
                  },
                },
              ]
            : [
                {
                  type: 'text',
                  text: msg.text,
                },
              ],
        })),
        ...userMessages.map((msg) => {
          if (msg.type === 'image_url') {
            return {
              role: 'user',
              content: [
                {
                  type: 'image',
                  source: {
                    type: 'url',
                    url: msg.text,
                    // Explicitly only include url for URL type
                  },
                },
              ],
            };
          } else if (msg.type === 'image_file') {
            // Find the corresponding local image for proper media type
            const localImage = localImages.find(img => img.file.name === msg.fileName);
            return {
              role: 'user',
              content: [
                {
                  type: 'image',
                  source: {
                    type: 'base64',
                    media_type: localImage?.mediaType || 'image/jpeg',
                    data: localImage?.base64Data || '',
                    // Explicitly only include required fields for base64 type
                  },
                },
              ],
            };
          } else {
            return {
              role: 'user',
              content: [
                {
                  type: 'text',
                  text: msg.text,
                },
              ],
            };
          }
        }),
      ],
    };

    try {
      const response = await axios.post('http://127.0.0.1:8000/chat', payload);
      const llmResponse = response.data;

      // Handle the new response format: {"text": "...", "image": ["url1", "url2", ...]}
      console.log('🔍 Raw LLM Response:', llmResponse);
      let botMessage: Message;
      
      if (typeof llmResponse === 'object' && llmResponse.text) {
        // New structured response format
        console.log('✅ Using structured response format');
        console.log('📝 Text:', llmResponse.text.substring(0, 100) + '...');
        console.log('🖼️ Images:', llmResponse.image);
        
        botMessage = {
          sender: 'Jib AI',
          text: llmResponse.text,
          type: 'text',
          images: llmResponse.image && llmResponse.image.length > 0 ? llmResponse.image : undefined
        };
      } else {
        // Fallback for plain text response
        console.log('⚠️ Using fallback text response format');
        botMessage = {
          sender: 'Jib AI',
          text: typeof llmResponse === 'string' ? llmResponse : JSON.stringify(llmResponse),
          type: 'text'
        };
      }
      
      console.log('💬 Final bot message:', botMessage);

      // Add the LLM's response to the conversation
      setMessages((prev) => [...prev, botMessage]);

      // Clear the input fields
      setImageUrls('');
      setTextQuery('');
      setImagePreviewUrls([]);
      setLocalImages([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Error sending message', error);
    }
  };

  // Handle key down event for text query
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      sendMessage();
      e.preventDefault();
    }
  };

  const totalImages = imagePreviewUrls.length + localImages.length;

  return (
    <div className="flex flex-col justify-between items-center min-h-screen bg-white">
      <div className='font-bold p-4 bg-white w-full fixed top-0 text-center border-b-black border-b-2 flex justify-between items-center'>
        <div></div>
        <div>HDmall Jib AI - Vision Testing</div>
        <button 
          onClick={() => setMessages([])}
          style={styles.clearChatButton}
          title="Clear chat history"
        >
          🗑️ Clear
        </button>
      </div>
      
      <div className='flex-1 w-full h-max overflow-y-auto p-4 border-1 border-black bg-white mb-4 mt-16' style={styles.chatBox}>
        {messages.map((msg, idx) => (
          <div key={idx} style={msg.sender === 'User' ? styles.userMessage : styles.llmMessage}>
            {msg.type === 'image_url' ? (
              <>
                <strong>{msg.sender}:</strong> <br />
                <img src={msg.text} alt="User uploaded" style={styles.image} />
              </>
            ) : msg.type === 'image_file' ? (
              <>
                <strong>{msg.sender}:</strong> <br />
                <img src={msg.text} alt={`File: ${msg.fileName}`} style={styles.image} />
                <div style={styles.fileName}>📁 {msg.fileName}</div>
              </>
            ) : (
              <>
                <strong>{msg.sender}:</strong> {msg.text}
                {/* Render bot images if present */}
                {msg.sender === 'Jib AI' && msg.images && msg.images.length > 0 && (
                  <div style={styles.botImagesContainer}>
                    <div style={styles.botImagesLabel}>📸 Related Images:</div>
                    <div style={styles.botImagesGrid}>
                      {msg.images.map((imageUrl, imgIdx) => (
                        <div key={imgIdx} style={styles.botImageItem}>
                          <img 
                            src={imageUrl} 
                            alt={`Bot image ${imgIdx + 1}`} 
                            style={styles.botImage}
                            onError={(e) => {
                              console.error(`Failed to load image: ${imageUrl}`);
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <div style={styles.botImageCaption}>Image {imgIdx + 1}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      <div className='w-full p-4 bg-white fixed bottom-0' style={{minHeight: '300px'}}>
        {/* Image URLs Input */}
        <div className='mb-3'>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            📸 Image URLs (one per line):
          </label>
          <textarea
            value={imageUrls}
            onChange={handleImageUrlsChange}
            style={styles.textarea}
            placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg&#10;..."
            rows={2}
          />
        </div>

        {/* Local File Upload */}
        <div className='mb-3'>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            📁 Local Image Files:
          </label>
          <div className='flex gap-2 mb-2'>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
              style={styles.fileInput}
            />
            <button
              onClick={clearLocalImages}
              style={styles.clearButton}
              disabled={localImages.length === 0}
            >
              Clear Files
            </button>
          </div>
          
          {localImages.length > 0 && (
            <div className='text-sm text-gray-600 mb-2'>
              📎 Selected: {localImages.map(img => img.file.name).join(', ')}
            </div>
          )}
        </div>

        {/* Combined Image Previews */}
        {totalImages > 0 && (
          <div className='mb-3'>
            <div className='text-sm text-gray-600 mb-2'>
              🔍 Total Images: {imagePreviewUrls.length} URLs + {localImages.length} Files = {totalImages}
            </div>
            <div style={styles.previewContainer}>
              {/* URL Image Previews */}
              {imagePreviewUrls.map((url, idx) => (
                <div key={`url-${idx}`} style={styles.previewItem}>
                  <img 
                    src={url} 
                    alt={`URL ${idx + 1}`} 
                    style={styles.preview}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  <div style={styles.previewLabel}>🌐 URL {idx + 1}</div>
                </div>
              ))}
              
              {/* Local File Previews */}
              {localImages.map((localImage, idx) => (
                <div key={`file-${idx}`} style={styles.previewItem}>
                  <img 
                    src={localImage.preview} 
                    alt={localImage.file.name} 
                    style={styles.preview}
                  />
                  <div style={styles.previewLabel}>📁 {localImage.file.name}</div>
                  <button
                    onClick={() => removeLocalImage(idx)}
                    style={styles.removeButton}
                  >
                    ❌
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Text Query Input */}
        <div className='mb-3'>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            💬 Text Query:
          </label>
          <div className='flex w-full'>
            <input
              type="text"
              value={textQuery}
              onChange={(e) => setTextQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              style={styles.input}
              placeholder="What do you see in these images?"
            />
            <button 
              onClick={sendMessage} 
              style={styles.button}
              disabled={!textQuery.trim() && totalImages === 0}
            >
              Send ({totalImages} 📸)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Styles
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    backgroundColor: '#1f2937',
  },
  chatBox: {
    flex: 1,
    width: '100%',
    maxHeight: 'calc(100vh - 380px)', // Adjust for larger input area
    overflowY: 'auto' as const,
    padding: '20px',
    backgroundColor: '#1f2937',
    marginBottom: '20px',
  },
  userMessage: {
    backgroundColor: '#0099ff',
    color: 'white',
    padding: '15px',
    borderRadius: '10px',
    marginBottom: '10px',
    alignSelf: 'flex-end' as const,
    maxWidth: '70%',
    width: 'fit-content',
    wordWrap: 'break-word' as const,
    marginLeft: 'auto',
    marginRight: '0',
  },
  llmMessage: {
    backgroundColor: '#808080',
    color: 'white',
    padding: '15px',
    borderRadius: '10px',
    marginBottom: '10px',
    alignSelf: 'flex-start' as const,
    whiteSpace: 'pre-wrap' as const,
    maxWidth: '70%',
    width: 'fit-content',
    wordWrap: 'break-word' as const,
    marginLeft: '0', 
    marginRight: 'auto',
  },
  textarea: {
    width: '100%',
    padding: '10px',
    borderRadius: '5px',
    border: '2px solid #ccc',
    backgroundColor: '#f9f9f9',
    fontFamily: 'monospace',
    fontSize: '14px',
    resize: 'vertical' as const,
  },
  input: {
    flex: 1,
    padding: '10px',
    borderRadius: '5px',
    border: '2px solid #ccc',
    marginRight: '10px',
    backgroundColor: '#f9f9f9',
  },
  button: {
    padding: '10px 20px',
    backgroundColor: '#0070f3',
    color: 'white',
    borderRadius: '5px',
    border: 'none',
    cursor: 'pointer',
    minWidth: '120px',
    fontWeight: 'bold' as const,
  },
  fileInput: {
    padding: '8px',
    borderRadius: '5px',
    border: '2px solid #ccc',
    backgroundColor: '#f9f9f9',
    flex: 1,
  },
  clearButton: {
    padding: '8px 15px',
    backgroundColor: '#dc3545',
    color: 'white',
    borderRadius: '5px',
    border: 'none',
    cursor: 'pointer',
  },
  image: {
    maxWidth: '100%',
    maxHeight: '200px',
    borderRadius: '10px',
  },
  fileName: {
    fontSize: '12px',
    color: '#ccc',
    marginTop: '5px',
  },
  previewContainer: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap' as const,
    maxHeight: '120px',
    overflowY: 'auto' as const,
  },
  previewItem: {
    position: 'relative' as const,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
  },
  preview: {
    width: '60px',
    height: '60px',
    objectFit: 'cover' as const,
    borderRadius: '5px',
    border: '1px solid #ddd',
  },
  previewLabel: {
    fontSize: '10px',
    color: '#666',
    marginTop: '2px',
    textAlign: 'center' as const,
    maxWidth: '60px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  removeButton: {
    position: 'absolute' as const,
    top: '-5px',
    right: '-5px',
    background: 'red',
    color: 'white',
    border: 'none',
    borderRadius: '50%',
    width: '20px',
    height: '20px',
    fontSize: '10px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  clearChatButton: {
    padding: '5px 10px',
    backgroundColor: '#6c757d',
    color: 'white',
    borderRadius: '5px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '12px',
  },
  botImagesContainer: {
    marginTop: '15px',
    padding: '10px',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
  },
  botImagesLabel: {
    fontSize: '14px',
    fontWeight: 'bold' as const,
    marginBottom: '10px',
    color: '#fff',
  },
  botImagesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '10px',
  },
  botImageItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '6px',
    padding: '8px',
  },
  botImage: {
    width: '100%',
    maxWidth: '200px',
    height: 'auto',
    maxHeight: '150px',
    objectFit: 'contain' as const,
    borderRadius: '6px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
  },
  botImageCaption: {
    fontSize: '12px',
    color: '#ccc',
    marginTop: '5px',
    textAlign: 'center' as const,
  },
};

export default Chat;
