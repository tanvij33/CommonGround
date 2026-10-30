import React from "react";
import { Compass, Heart } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-borderline/60 bg-white/60 py-10 px-4 sm:px-6 lg:px-8 select-none">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-500 font-mono">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded-full bg-nearblack flex items-center justify-center text-white">
            <Compass className="w-3 h-3 text-brand-violet" />
          </div>
          <span className="font-bold text-nearblack font-sans">Common Ground</span>
          <span>© {new Date().getFullYear()}</span>
        </div>

        <div className="flex items-center gap-6">
          <a
            href="https://docs.qloo.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-nearblack transition-colors"
          >
            Qloo Docs
          </a>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-nearblack transition-colors"
          >
            FastAPI Swagger
          </a>
          <a
            href="http://localhost:8000/health/qloo"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-nearblack transition-colors"
          >
            API Health
          </a>
        </div>

        <div className="text-center sm:text-right">
          <span>Powered by Qloo Cultural AI</span>
        </div>
      </div>
    </footer>
  );
};

