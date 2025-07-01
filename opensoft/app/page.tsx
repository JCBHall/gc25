/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
  Send,
  Smile,
  Sun,
  Moon,
  Coffee,
  Heart,
  AlertCircle,
  UserIcon,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { baseURL } from "@/lib/helperFunctions";

type MessageType = {
  id: string;
  content: string;
  sender: "bot" | "user" | string;
  timestamp: Date;
};

const quickResponses = [
  { text: "I'm doing great!", icon: <Sun className="mr-2 h-4 w-4" /> },
  { text: "Just okay", icon: <Coffee className="mr-2 h-4 w-4" /> },
  { text: "Feeling down", icon: <Moon className="mr-2 h-4 w-4" /> },
  { text: "Need support", icon: <Heart className="mr-2 h-4 w-4" /> },
];

// Create a global WebSocket instance that persists across renders
let globalWs: WebSocket | null = null;

export default function ChatApp() {
  // State variables
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(true);

  // Stats and animations
  const [streakDays, setStreakDays] = useState(0);
  const [wellnessPoints, setWellnessPoints] = useState(0);
  const [level, setLevel] = useState(0);
  const [levelProgress, setLevelProgress] = useState(0);
  const [showStreakAnimation, setShowStreakAnimation] = useState(false);
  const [showPointsAnimation, setShowPointsAnimation] = useState(false);
  const [showLevelUpAnimation, setShowLevelUpAnimation] = useState(false);
  const [pointsToAdd, setPointsToAdd] = useState(0);

  // User info
  const [userName, setUserName] = useState("");
  const [empId, setEmpId] = useState("");

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isMountedRef = useRef(false);

  // Fetch chat history
  useEffect(() => {
    const fetchChatHistory = async () => {
      setIsLoadingHistory(true);

      try {
        const token = localStorage.getItem("token");
        if (!token) {
          setConnectionError(
            "Authentication token not found. Please log in again."
          );
          setIsLoadingHistory(false);
          return;
        }

        const response = await fetch(
          `${baseURL}/a/api/v1/emp/details/user/chats`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch chat history: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
          const {
            chats,
            name,
            empid,
            lastActive,
            level,
            levelProgress,
            streakDays,
            wellnessPoints,
          } = data.data.userChats;

          // Set user info
          setUserName(name || "");
          setEmpId(empid || "");

          // Set stats
          setLevel(level || 0);
          setLevelProgress(levelProgress || 0);
          setStreakDays(streakDays || 0);
          setWellnessPoints(wellnessPoints || 0);

          // Format chat history to our MessageType format
          const formattedMessages: MessageType[] = [];

          if (chats && Array.isArray(chats)) {
            // Process each chat message
            for (let i = 0; i < chats.length; i++) {
              const chat = chats[i];

              // Skip empty messages
              if (!chat || !chat.message) continue;

              // Convert sender types to our format
              let senderType: "bot" | "user" | string;
              if (chat.sender === "ai") {
                senderType = "bot";
              } else if (chat.sender === "user") {
                senderType = "user";
              } else {
                // Handle other senders (e.g., "Rahul Verma")
                senderType = chat.sender;
              }

              // Try to properly parse JSON messages
              let content = chat.message;
              try {
                // Check if the message is a JSON string (starting with "{")
                if (
                  typeof content === "string" &&
                  content.trim().startsWith("{")
                ) {
                  const parsedJson = JSON.parse(content);
                  if (parsedJson.content) {
                    content = parsedJson.content;
                  } else if (
                    parsedJson.type === "ping" ||
                    parsedJson.type === "presence"
                  ) {
                    // Skip system messages
                    continue;
                  }
                }
              } catch (e) {
                // Not a valid JSON, use original message
              }

              formattedMessages.push({
                id: i.toString(),
                content: content,
                sender: senderType,
                timestamp: new Date(chat.timestamp),
              });
            }
          }

          setMessages(formattedMessages);
        } else {
          throw new Error(data.message || "Failed to fetch chat history");
        }
      } catch (error) {
        console.error("Error fetching chat history:", error);
        setConnectionError(
          "Failed to load chat history. Will try to connect to chat service."
        );
        // Initialize with empty messages if history fails
        setMessages([]);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    fetchChatHistory();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // One-time WebSocket setup
  useEffect(() => {
    // Only set up WebSocket once after history is loaded
    if (!isLoadingHistory && !isMountedRef.current) {
      isMountedRef.current = true;
      initializeWebSocket();
    }

    return () => {
      // Cleanup on component unmount
      if (globalWs && globalWs.readyState === WebSocket.OPEN) {
        try {
          // Send offline status before closing
          globalWs.send(
            JSON.stringify({
              type: "presence",
              status: "offline",
            })
          );
          globalWs.close(1000, "Component unmounted");
        } catch (error) {
          console.error("Error closing WebSocket:", error);
        }
      }
    };
  }, [isLoadingHistory]);

  // Initialize WebSocket connection
  const initializeWebSocket = () => {
    if (globalWs && globalWs.readyState === WebSocket.OPEN) {
      setIsConnected(true);
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      setConnectionError(
        "Authentication token not found. Please log in again."
      );
      return;
    }

    try {
      // Close existing connection if necessary
      if (globalWs) {
        try {
          globalWs.close();
        } catch (e) {
          console.error("Error closing WebSocket:", e);
        }
      }

      // Create new connection
      const wsUrl = `ws://52.66.116.15/c/ws/wsconnect/${token}`;
      globalWs = new WebSocket(wsUrl);

      // Connection opened
      globalWs.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
      };

      // Connection error
      globalWs.onerror = (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
        setConnectionError("Connection error. Please try again.");
      };

      // Connection closed
      globalWs.onclose = (event) => {
        setIsConnected(false);

        if (event.code !== 1000) {
          setConnectionError(
            "Connection closed. Please try sending a message to reconnect."
          );
        }
      };

      // Message received
      globalWs.onmessage = (event) => {
        try {
          // Skip pong messages
          if (event.data === '{"type":"pong"}') {
            return;
          }

          // Try to parse as JSON
          let data;
          try {
            data = JSON.parse(event.data);
          } catch (parseError) {
            // Handle text messages
            if (
              typeof event.data === "string" &&
              event.data.trim().length > 0
            ) {
              const botMessage: MessageType = {
                id: Date.now().toString(),
                content: event.data,
                sender: "bot",
                timestamp: new Date(),
              };

              setMessages((prevMessages) => [...prevMessages, botMessage]);
              setIsTyping(false);
            }
            return;
          }

          // Handle different message types
          if (data.type === "message") {
            const botMessage: MessageType = {
              id: data.id || Date.now().toString(),
              content: data.content || "Message received with no content",
              sender: "bot",
              timestamp: new Date(),
            };

            setMessages((prevMessages) => [...prevMessages, botMessage]);
            setIsTyping(false);

            // Handle points
            if (data.points) {
              handlePointsUpdate(data.points);
            }
          } else if (data.type === "typing") {
            setIsTyping(true);
          } else if (data.type === "stats_update") {
            // Update stats
            if (data.streakDays !== undefined) {
              setStreakDays(data.streakDays);
              if (data.streakChange > 0) {
                setShowStreakAnimation(true);
                setTimeout(() => setShowStreakAnimation(false), 3000);
              }
            }

            if (data.wellnessPoints !== undefined) {
              const oldLevel = Math.floor(wellnessPoints / 100);
              const newLevel = Math.floor(data.wellnessPoints / 100);

              setWellnessPoints(data.wellnessPoints);

              if (newLevel > oldLevel) {
                setLevel(newLevel);
                setShowLevelUpAnimation(true);
                setTimeout(() => setShowLevelUpAnimation(false), 3000);
              }
            }
          }
        } catch (error) {
          console.error("Error handling WebSocket message:", error);
        }
      };
    } catch (error) {
      console.error("Error creating WebSocket:", error);
      if (error instanceof Error) {
        setConnectionError(`Failed to connect: ${error.message}`);
      } else {
        setConnectionError("Failed to connect: Unknown error");
      }
    }
  };

  // Handle points update
  const handlePointsUpdate = (points: number) => {
    setPointsToAdd(points);
    setShowPointsAnimation(true);

    setTimeout(() => {
      setWellnessPoints((prev) => {
        const newPoints = prev + points;
        const oldLevel = Math.floor(prev / 100);
        const newLevel = Math.floor(newPoints / 100);

        // Check if user leveled up
        if (newLevel > oldLevel) {
          setLevel(newLevel);
          setShowLevelUpAnimation(true);
          setTimeout(() => setShowLevelUpAnimation(false), 3000);
        }

        return newPoints;
      });

      // Hide points animation after delay
      setTimeout(() => setShowPointsAnimation(false), 1000);
    }, 500);
  };

  // Fallback response when WebSocket is unavailable
  const fallbackResponse = () => {
    setIsTyping(true);

    // Generate random points
    const pointsEarned = Math.floor(Math.random() * 15) + 5;
    setTimeout(() => {
      handlePointsUpdate(pointsEarned);
    }, 500);

    // Random streak update
    if (Math.random() > 0.7) {
      setTimeout(() => {
        setStreakDays((prev) => prev + 1);
        setShowStreakAnimation(true);
        setTimeout(() => setShowStreakAnimation(false), 3000);
      }, 2000);
    }

    // Generate bot response
    setTimeout(() => {
      const botResponses = [
        "Thanks for sharing! How else can I support you today?",
        "I appreciate your openness. Would you like to talk more about that?",
        "That's good to know. Remember, it's okay to have all kinds of feelings.",
        "I'm here for you. What would help you feel better right now?",
        "Thank you for checking in today. Is there anything specific on your mind?",
      ];

      const randomResponse =
        botResponses[Math.floor(Math.random() * botResponses.length)];

      const botMessage: MessageType = {
        id: Date.now().toString(),
        content: randomResponse,
        sender: "bot",
        timestamp: new Date(),
      };

      setMessages((prevMessages) => [...prevMessages, botMessage]);
      setIsTyping(false);
    }, 1500);
  };

  // Send message function - simplified to be like Postman
  const handleSendMessage = (content: string) => {
    if (!content.trim()) return;

    // Create user message
    const userMessage: MessageType = {
      id: Date.now().toString(),
      content,
      sender: "user",
      timestamp: new Date(),
    };

    // Add user message to chat
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput("");

    // Award points for user message
    handlePointsUpdate(10);

    // Check WebSocket connection
    if (!isConnected || !globalWs || globalWs.readyState !== WebSocket.OPEN) {
      // Try to reconnect
      initializeWebSocket();

      // Wait brief period for connection to establish
      setTimeout(() => {
        if (globalWs && globalWs.readyState === WebSocket.OPEN) {
          sendSingleMessage(content, userMessage.id);
        } else {
          fallbackResponse();
        }
      }, 1000);
    } else {
      // Send message if connected
      sendSingleMessage(content, userMessage.id);
    }
  };

  // Simple function to send a single message
  const sendSingleMessage = (content: string, messageId: string) => {
    if (!globalWs || globalWs.readyState !== WebSocket.OPEN) {
      fallbackResponse();
      return;
    }

    try {
      // Simple message object - like Postman
      const messageData = {
        type: "message",
        content: content,
        id: messageId,
        timestamp: new Date().toISOString(),
      };

      // Send the message
      globalWs.send(JSON.stringify(messageData));
      setIsTyping(true);
    } catch (error) {
      console.error("Error sending message:", error);
      fallbackResponse();
    }
  };

  // Function to format a timestamp
  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Function to format a date for grouping messages
  const formatDate = (date: Date) => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return "Today";
    } else if (date.toDateString() === yesterday.toDateString()) {
      return "Yesterday";
    } else {
      return date.toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      });
    }
  };

  // Sort and group messages by date
  const getGroupedAndSortedMessages = () => {
    const groups: Record<string, MessageType[]> = {};

    // Only process if we have messages
    if (messages && messages.length > 0) {
      // Group messages by date
      messages.forEach((message) => {
        if (!message || !message.timestamp) return;

        const date = formatDate(new Date(message.timestamp));
        if (!groups[date]) {
          groups[date] = [];
        }
        groups[date].push(message);
      });
    }

    // Sort dates chronologically with Today and Yesterday at the end
    const getSortValue = (date: string) => {
      if (date === "Today") return 3;
      if (date === "Yesterday") return 2;
      return 1; // Other dates
    };

    // Sort dates with Today last (most recent)
    const sortedDates = Object.keys(groups).sort((a, b) => {
      const aValue = getSortValue(a);
      const bValue = getSortValue(b);

      if (aValue !== bValue) {
        return aValue - bValue; // Sort by special values first
      }

      if (aValue === 1) {
        // Both are regular dates
        return new Date(a).getTime() - new Date(b).getTime();
      }

      return 0;
    });

    return { groups, sortedDates };
  };

  const { groups: groupedMessages, sortedDates } =
    getGroupedAndSortedMessages();

  // Toggle stats display on mobile
  const toggleStats = () => {
    setShowStats(!showStats);
  };

  return (
    <main className="flex min-h-screen w-full flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 p-0 sm:p-2 md:p-4">
      <div className="z-10 flex h-full w-full max-w-4xl items-center justify-center pt-2 sm:pt-16">
        <Card className="flex h-[90vh] w-full flex-col overflow-hidden rounded-none border border-gray-200 bg-white/70 shadow-lg backdrop-blur-lg sm:h-[90vh] sm:rounded-xl">
          <div className="border-b border-gray-200 bg-white/80 p-2 sm:p-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div className="mb-2 sm:mb-0">
                <h1 className="text-xl font-bold text-[#18181B] sm:text-2xl">
                  Mental Wellness Chat
                </h1>
                <p className="text-xs text-[#6F7985] sm:text-sm">
                  {userName
                    ? `Hello, ${userName} (${empId})`
                    : "A safe space to check in and share how you're feeling"}
                </p>
              </div>

              {/* Mobile toggle button */}
              <div className="flex items-center justify-between sm:hidden">
                <div className="flex items-center">
                  {connectionError ? (
                    <div className="mr-2 flex items-center text-red-500">
                      <AlertCircle className="mr-1 h-3 w-3" />
                      <span className="text-xs">Offline</span>
                    </div>
                  ) : isConnected ? (
                    <div className="mr-2 flex items-center text-green-500">
                      <div className="mr-1 h-2 w-2 animate-pulse rounded-full bg-green-500" />
                      <span className="text-xs">Online</span>
                    </div>
                  ) : (
                    <div className="mr-2 flex items-center text-yellow-500">
                      <div className="mr-1 h-2 w-2 animate-pulse rounded-full bg-yellow-500" />
                      <span className="text-xs">Connecting...</span>
                    </div>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleStats}
                  className="ml-2 p-1"
                >
                  {showStats ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {/* Connection status indicator - Desktop */}
              <div className="hidden sm:block">
                {connectionError ? (
                  <div className="mr-4 flex items-center text-red-500">
                    <AlertCircle className="mr-1 h-4 w-4" />
                    <span className="text-xs">Offline</span>
                  </div>
                ) : isConnected ? (
                  <div className="mr-4 flex items-center text-green-500">
                    <div className="mr-1 h-2 w-2 animate-pulse rounded-full bg-green-500" />
                    <span className="text-xs">Online</span>
                  </div>
                ) : (
                  <div className="mr-4 flex items-center text-yellow-500">
                    <div className="mr-1 h-2 w-2 animate-pulse rounded-full bg-yellow-500" />
                    <span className="text-xs">Connecting...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Stats with animations - Collapsible on mobile */}
            <div
              className={`${showStats ? "flex" : "hidden"} mt-2 flex-wrap items-center justify-center gap-2 sm:mt-0 sm:flex sm:justify-end sm:gap-4`}
            >
              <div className="relative flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs sm:px-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="h-3 w-3 text-green-600 sm:h-4 sm:w-4"
                >
                  <path d="M2 20h.01M7 20v-4M12 20v-8M17 20v-12M22 20v-16" />
                </svg>
                <span className="text-xs font-semibold text-green-800">
                  {level}
                  <span className="xs:inline ml-1 hidden text-xs text-green-600">
                    ({wellnessPoints % 100}/100)
                  </span>
                </span>
                <AnimatePresence>
                  {showLevelUpAnimation && (
                    <motion.div
                      className="absolute -top-6 left-0"
                      initial={{ y: 0, opacity: 0 }}
                      animate={{ y: -20, opacity: 1 }}
                      exit={{ y: -40, opacity: 0 }}
                    >
                      <div className="rounded-full bg-green-500 px-2 py-1 text-xs font-bold text-white">
                        Level Up!
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="relative flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs sm:px-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="h-3 w-3 text-amber-600 sm:h-4 sm:w-4"
                >
                  <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
                </svg>
                <span className="text-xs font-semibold text-amber-800">
                  {streakDays}
                  <span className="xs:inline hidden">
                    {streakDays !== 1 ? " days" : " day"}
                  </span>
                </span>
                <AnimatePresence>
                  {showStreakAnimation && (
                    <motion.div
                      className="absolute -top-2 -right-2"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                    >
                      <div className="rounded-full bg-amber-500 px-1.5 py-0.5 text-xs font-bold text-white">
                        +1
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="relative flex items-center gap-1 rounded-full bg-purple-100 px-2 py-1 text-xs sm:px-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="h-3 w-3 text-purple-600 sm:h-4 sm:w-4"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                </svg>
                <span className="text-xs font-semibold text-purple-800">
                  {wellnessPoints} pts
                </span>
                <AnimatePresence>
                  {showPointsAnimation && (
                    <motion.div
                      className="absolute -top-2 -right-2"
                      initial={{ y: 0, opacity: 0, scale: 0.5 }}
                      animate={{ y: -15, opacity: 1, scale: 1 }}
                      exit={{ y: -30, opacity: 0 }}
                      transition={{ duration: 1 }}
                    >
                      <div className="rounded-full bg-purple-500 px-1.5 py-0.5 text-xs font-bold text-white">
                        +{pointsToAdd}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* Chat interface */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {connectionError && (
              <div className="bg-red-50 p-2 text-center text-xs text-red-800 sm:text-sm">
                <AlertCircle className="mr-1 inline h-3 w-3 sm:h-4 sm:w-4" />
                {connectionError}
              </div>
            )}

            {isLoadingHistory ? (
              <div className="flex flex-1 items-center justify-center">
                <div className="text-center">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-b-2 border-gray-900 sm:h-8 sm:w-8"></div>
                  <p className="mt-2 text-xs text-gray-600 sm:text-sm">
                    Loading your conversation history...
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex-1 space-y-2 overflow-y-auto p-2 pt-4 sm:space-y-4 sm:p-4 sm:pt-6">
                {/* Show grouped messages by date */}
                {sortedDates.map((date) => (
                  <div key={date} className="space-y-2 sm:space-y-4">
                    <div className="sticky top-0 z-10 my-2 flex items-center justify-center sm:my-4">
                      <div className="rounded-full bg-gray-200 px-2 py-1 text-xs font-medium text-gray-600">
                        {date}
                      </div>
                    </div>

                    {groupedMessages[date].map((message) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
                      >
                        {message.sender !== "user" && (
                          <Avatar className="mr-1 flex h-6 w-6 items-center justify-center bg-[#18181B] sm:mr-2 sm:h-8 sm:w-8">
                            {message.sender === "bot" ? (
                              <Smile className="h-4 w-4 text-[#F7FBFD] sm:h-5 sm:w-5" />
                            ) : (
                              <UserIcon className="h-4 w-4 text-[#F7FBFD] sm:h-5 sm:w-5" />
                            )}
                          </Avatar>
                        )}
                        <div
                          className={`max-w-[80%] rounded-xl px-3 py-1.5 text-sm sm:max-w-[85%] sm:rounded-2xl sm:px-4 sm:py-2 ${
                            message.sender === "user"
                              ? "bg-[#18181B] text-[#F7FBFD]"
                              : "bg-[#F4F4F5]"
                          }`}
                        >
                          {message.sender !== "user" &&
                            message.sender !== "bot" && (
                              <p className="mb-1 text-xs font-medium text-gray-500">
                                {message.sender}
                              </p>
                            )}
                          <p>{message.content}</p>
                          <p className="mt-1 text-[10px] opacity-70 sm:text-xs">
                            {formatTime(new Date(message.timestamp))}
                          </p>
                        </div>
                        {message.sender === "user" && (
                          <Avatar className="ml-1 flex h-6 w-6 items-center justify-center bg-gray-200 sm:ml-2 sm:h-8 sm:w-8">
                            <div className="text-[10px] font-medium sm:text-xs">
                              You
                            </div>
                          </Avatar>
                        )}
                      </motion.div>
                    ))}
                  </div>
                ))}

                {isTyping && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <Avatar className="mr-1 h-6 w-6 bg-[#18181B] sm:mr-2 sm:h-8 sm:w-8">
                      <Smile className="h-4 w-4 text-[#F7FBFD] sm:h-5 sm:w-5" />
                    </Avatar>
                    <div className="rounded-xl bg-[#F4F4F5] px-3 py-1.5 sm:rounded-2xl sm:px-4 sm:py-2">
                      <div className="flex space-x-1">
                        {[0, 150, 300].map((delay) => (
                          <motion.div
                            key={delay}
                            className="h-1.5 w-1.5 rounded-full bg-gray-400 sm:h-2 sm:w-2"
                            animate={{ y: [0, -6, 0] }}
                            transition={{
                              repeat: Infinity,
                              duration: 0.8,
                              delay: delay / 1000,
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}

            <div className="bg-[#FFFFFF]/50 px-2 py-1 backdrop-blur-sm sm:px-4 sm:py-2">
              <div className="mb-1 flex flex-wrap gap-1 sm:mb-2 sm:gap-2">
                {quickResponses.map((response, index) => (
                  <motion.div
                    key={index}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex h-7 items-center bg-white/80 px-2 text-xs transition-all duration-200 hover:bg-[#F4F4F5] sm:h-9 sm:px-3 sm:text-sm"
                      onClick={() => handleSendMessage(response.text)}
                    >
                      {response.icon}
                      {response.text}
                    </Button>
                  </motion.div>
                ))}
              </div>

              <div className="border-t border-gray-200 bg-[#FFFFFF]/50 p-2 backdrop-blur-sm sm:p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage(input);
                  }}
                  className="flex space-x-2"
                >
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    className="h-9 flex-1 border-gray-200 bg-white/80 text-sm sm:h-10"
                    disabled={isLoadingHistory}
                  />
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Button
                      type="submit"
                      size="icon"
                      className="h-9 w-9 sm:h-10 sm:w-10"
                      disabled={isLoadingHistory}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </motion.div>
                </form>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Dynamic background blobs that adjust to viewport */}
      <div className="animate-blob fixed -top-10 -left-20 h-56 w-56 rounded-full bg-purple-200 opacity-30 mix-blend-multiply blur-3xl sm:top-20 sm:left-10 sm:h-72 sm:w-72" />
      <div className="animate-blob animation-delay-2000 fixed top-20 right-0 h-56 w-56 rounded-full bg-yellow-200 opacity-30 mix-blend-multiply blur-3xl sm:top-40 sm:right-10 sm:h-72 sm:w-72" />
      <div className="animate-blob animation-delay-4000 fixed bottom-20 left-40 hidden h-72 w-72 rounded-full bg-pink-200 opacity-30 mix-blend-multiply blur-3xl sm:block" />
    </main>
  );
}
