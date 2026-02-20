import React, { useState, useRef, useEffect } from 'react';
import { Send, RefreshCw, FileText, CheckCircle2, ShoppingBag, HelpCircle, Bot, User, Trash2, Plus, ShoppingCart, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PRODUCTS, CATEGORIES } from './data/products';

const App = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hello! 👋 Welcome to **UrbanStyle E-Commerce**. I'm your AI assistant.\n\nYou can browse our catalog, add items to your cart, and I'll help you generate a professional invoice for your order!",
      sender: 'bot',
      type: 'info',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [cart, setCart] = useState([]);
  const [showCatalog, setShowCatalog] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text = input) => {
    const messageText = text.trim();
    if (!messageText) return;

    const userMessage = {
      id: Date.now(),
      text: messageText,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      const data = await response.json();
      setIsTyping(false);

      if (data.error) {
        addBotMessage('⚠️ Sorry, I encountered an error. Please try again.', 'error');
      } else {
        addBotMessage(data.response, data.type, data.saved_invoice_id);
      }
    } catch (error) {
      setIsTyping(false);
      addBotMessage('⚠️ Server connection failed. Is the backend running?', 'error');
    }
  };

  const addBotMessage = (text, type, invoiceId) => {
    const botMessage = {
      id: Date.now(),
      text,
      sender: 'bot',
      type: type || 'info',
      invoiceId,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, botMessage]);
  };

  const addToCart = (product) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item);
      }
      return [...prev, { ...product, quantity: 1 }];
    });
  };

  const checkout = () => {
    if (cart.length === 0) {
      addBotMessage("Your cart is empty! Please add some items first.", "warning");
      return;
    }
    const itemsStr = cart.map(item => `${item.quantity}x ${item.name} @ ${item.price}`).join(', ');
    const checkoutMessage = `Generate invoice for my order: ${itemsStr}. Please ask for my name and shipping details if needed to complete the invoice.`;
    handleSend(checkoutMessage);
    setCart([]);
    setShowCatalog(false);
  };

  const filteredProducts = selectedCategory === 'All' 
    ? PRODUCTS 
    : PRODUCTS.filter(p => p.category === selectedCategory);

  return (
    <div className="flex h-screen bg-slate-50 relative overflow-hidden">
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary-200/30 rounded-full blur-3xl -z-10"></div>
      
      {/* Sidebar */}
      <div className="hidden lg:flex flex-col w-80 m-6 glass-effect rounded-3xl p-8 shadow-xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-primary-600 p-2 rounded-xl text-white shadow-lg">
            <ShoppingBag size={24} />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">UrbanStyle</h1>
        </div>

        <div className="flex-1 space-y-6">
          <button 
            onClick={() => setShowCatalog(!showCatalog)}
            className="w-full flex items-center justify-between p-4 rounded-2xl bg-white shadow-sm border border-slate-100 hover:border-primary-400 transition-all font-semibold text-slate-700"
          >
            <span className="flex items-center gap-2"><ShoppingBag size={18}/> Browse Catalog</span>
            <Plus size={16} className={showCatalog ? 'rotate-45 transition-transform' : 'transition-transform'}/>
          </button>

          {cart.length > 0 && (
            <div className="bg-white rounded-3xl p-5 shadow-sm border border-slate-100">
              <h3 className="flex items-center gap-2 font-bold mb-4 text-slate-800"><ShoppingCart size={18}/> Your Cart</h3>
              <div className="space-y-3 max-h-48 overflow-y-auto pr-2 scrollbar-thin">
                {cart.map(item => (
                  <div key={item.id} className="flex justify-between text-xs font-medium">
                    <span className="text-slate-600">{item.quantity}x {item.name}</span>
                    <span className="text-slate-400">₹{item.price * item.quantity}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-slate-100">
                <div className="flex justify-between font-bold text-slate-800 mb-4">
                  <span>Total</span>
                  <span>₹{cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)}</span>
                </div>
                <button 
                  onClick={checkout}
                  className="w-full bg-primary-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-primary-200 hover:bg-primary-700 transition-all"
                >
                  Create Invoice
                </button>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-2">Quick Context</h4>
            <button onClick={() => handleSend("What are your shipping rates?")} className="w-full text-left p-3 text-sm text-slate-600 hover:bg-white rounded-xl transition-all">Shipping Rates</button>
            <button onClick={() => handleSend("Do you have any discounts?")} className="w-full text-left p-3 text-sm text-slate-600 hover:bg-white rounded-xl transition-all">Active Discounts</button>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-[calc(100vh-3rem)] m-6 lg:ml-0 glass-effect rounded-3xl shadow-xl overflow-hidden relative">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white/50">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center text-primary-600">
              <Bot size={24} />
            </div>
            <div>
              <h2 className="font-bold text-slate-800">Shopping Assistant</h2>
              <p className="text-[10px] text-green-500 font-bold uppercase tracking-widest">Always Here to Help</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}>
              <div className={`p-4 rounded-2xl max-w-[80%] shadow-sm leading-relaxed text-sm ${msg.sender === 'user' ? 'bg-primary-600 text-white rounded-tr-none' : 'bg-white text-slate-700 rounded-tl-none border border-slate-100'}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                {msg.invoiceId && (
                  <div className="mt-3 pt-3 border-t border-slate-100 text-[10px] font-bold text-primary-600 underline cursor-pointer">
                    Click to download invoice #{msg.invoiceId.split('-')[0]}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isTyping && <div className="text-slate-400 text-xs animate-pulse">Assistant is thinking...</div>}
          <div ref={messagesEndRef} />
        </div>

        {/* Catalog Overlay */}
        {showCatalog && (
          <div className="absolute inset-x-0 bottom-24 p-6 mx-6 bg-white shadow-2xl rounded-3xl border border-slate-100 z-20 animate-in slide-in-from-bottom-10">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-bold text-slate-800 text-lg">Product Catalog</h3>
              <div className="flex gap-2">
                {CATEGORIES.map(c => (
                  <button 
                    key={c} 
                    onClick={() => setSelectedCategory(c)}
                    className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${selectedCategory === c ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
                  >
                    {c}
                  </button>
                ))}
                <button onClick={() => setShowCatalog(false)} className="ml-2 text-slate-400 hover:text-red-500"><X size={20}/></button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-80 overflow-y-auto pr-2 scrollbar-thin">
              {filteredProducts.map(p => (
                <div key={p.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-primary-300 transition-all flex flex-col group">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold text-slate-800 text-sm">{p.name}</h4>
                    <span className="text-primary-600 font-bold text-xs">₹{p.price}</span>
                  </div>
                  <p className="text-[10px] text-slate-500 mb-4 line-clamp-2">{p.description}</p>
                  <button 
                    onClick={() => addToCart(p)}
                    className="mt-auto w-full py-2 bg-white rounded-xl text-primary-600 border border-primary-100 text-xs font-bold group-hover:bg-primary-600 group-hover:text-white transition-all shadow-sm"
                  >
                    Add to Cart
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-6 bg-white/50 border-t border-slate-100">
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="relative flex items-center gap-3">
            <button 
              type="button"
              onClick={() => setShowCatalog(!showCatalog)}
              className="p-4 bg-slate-100 text-slate-600 rounded-2xl hover:bg-primary-50 hover:text-primary-600 transition-all shadow-sm"
              title="Browse Catalog"
            >
              <Plus size={20}/>
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me about products or checkout your cart..."
              className="flex-1 bg-white border border-slate-200 rounded-2xl py-4 px-6 focus:ring-4 focus:ring-primary-100 focus:border-primary-400 transition-all outline-none shadow-sm text-sm"
              disabled={isTyping}
            />
            <button
              type="submit"
              disabled={isTyping || !input.trim()}
              className="p-4 bg-primary-600 text-white rounded-2xl hover:bg-primary-700 disabled:bg-slate-300 transition-all shadow-lg"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default App;
