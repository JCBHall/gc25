import { Smile, Frown, Meh, TrendingUp } from "lucide-react";

// Helper function to get mood icon
function getMoodIcon(mood: string) {
  switch (mood.toLowerCase()) {
    case "happy":
      return <Smile className="h-5 w-5 text-green-500" />;
    case "sad":
      return <Frown className="h-5 w-5 text-red-500" />;
    case "angry":
      return <Frown className="h-5 w-5 text-red-600" />;
    case "tending to happy":
      return <TrendingUp className="h-5 w-5 text-lime-500" />;
    case "neutral":
      return <Meh className="h-5 w-5 text-gray-500" />;
    default:
      return <Meh className="h-5 w-5 text-gray-500" />;
  }
}

// Helper function to get mood color
function getMoodColor(mood: string) {
  switch (mood.toLowerCase()) {
    case "happy":
      return "bg-green-100 text-green-800";
    case "sad":
      return "bg-red-100 text-red-800";
    case "angry":
      return "bg-red-100 text-red-800";
    case "tending to happy":
      return "bg-lime-100 text-lime-800";
    case "neutral":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

const baseURL = "http://52.66.116.15";

export { getMoodColor, getMoodIcon, baseURL };
