import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MobileMarkdownRendererProps {
  content: string;
}

export const MobileMarkdownRenderer: React.FC<MobileMarkdownRendererProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (code: string, index: number) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(code);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    }
  };

  const isSafeUrl = (url: string): boolean => {
    const trimmed = url.trim().toLowerCase();
    return (
      trimmed.startsWith('http://') ||
      trimmed.startsWith('https://') ||
      trimmed.startsWith('mailto:') ||
      trimmed.startsWith('/') ||
      trimmed.startsWith('#')
    );
  };

  // Split content by code blocks (```lang\n...\n```)
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-2 text-xs leading-relaxed text-slate-200 break-words">
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).trim().split('\n');
          const language = lines[0].trim().match(/^[a-zA-Z0-9_-]+$/) ? lines[0].trim() : '';
          const code = language ? lines.slice(1).join('\n') : lines.join('\n');

          return (
            <div
              key={index}
              className="my-2 rounded-xl bg-background-tertiary border border-border-subtle overflow-hidden font-mono text-[11px]"
            >
              <div className="px-3 py-1 bg-background-secondary/80 border-b border-border-subtle flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-semibold uppercase">{language || 'code'}</span>
                <button
                  onClick={() => handleCopy(code, index)}
                  className="flex items-center gap-1 text-[10px] hover:text-white transition"
                >
                  {copiedIndex === index ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3 overflow-x-auto text-slate-200">
                <code>{code}</code>
              </pre>
            </div>
          );
        }

        // Render plain text with paragraphs and links
        const paragraphs = part.split(/\n\n+/);
        return (
          <React.Fragment key={index}>
            {paragraphs.map((p, pIdx) => {
              if (!p.trim()) return null;

              // Parse Markdown links [text](url)
              const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
              const segments: React.ReactNode[] = [];
              let lastIndex = 0;
              let match: RegExpExecArray | null;

              while ((match = linkRegex.exec(p)) !== null) {
                if (match.index > lastIndex) {
                  segments.push(p.slice(lastIndex, match.index));
                }
                const label = match[1];
                const url = match[2];

                if (isSafeUrl(url)) {
                  segments.push(
                    <a
                      key={`${index}-${pIdx}-${match.index}`}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 underline underline-offset-2 hover:text-cyan-300"
                    >
                      {label}
                    </a>
                  );
                } else {
                  segments.push(
                    <span key={`${index}-${pIdx}-${match.index}`} className="text-rose-400">
                      [{label} (unsafe-link-blocked)]
                    </span>
                  );
                }
                lastIndex = match.index + match[0].length;
              }

              if (lastIndex < p.length) {
                segments.push(p.slice(lastIndex));
              }

              return (
                <p key={pIdx} className="whitespace-pre-wrap">
                  {segments}
                </p>
              );
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};
