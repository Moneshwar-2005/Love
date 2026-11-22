import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  // Simple, robust, dependency-free Markdown parser tailored for assistant output
  // Supports: Code blocks with language & copy button, inline code, bold, italic, lists, paragraphs, headers.

  const renderFormattedText = (text: string) => {
    // Process inline elements: bold, italic, inline code
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let keyIdx = 0;

    // Pattern for inline code `...`, bold **...**, italic *...*
    const inlineRegex = /(`([^`]+)`)|(\*\*([^*]+)\*\*)|(\*([^*]+)\*)/;

    while (remaining.length > 0) {
      const match = remaining.match(inlineRegex);
      if (!match || match.index === undefined) {
        parts.push(remaining);
        break;
      }

      if (match.index > 0) {
        parts.push(remaining.substring(0, match.index));
      }

      if (match[2]) {
        // Inline code `code`
        parts.push(
          <code
            key={keyIdx++}
            className="px-1.5 py-0.5 rounded bg-background-tertiary text-cyan-300 font-mono text-xs border border-border-subtle"
          >
            {match[2]}
          </code>
        );
      } else if (match[4]) {
        // Bold **text**
        parts.push(
          <strong key={keyIdx++} className="font-semibold text-slate-100">
            {match[4]}
          </strong>
        );
      } else if (match[6]) {
        // Italic *text*
        parts.push(
          <em key={keyIdx++} className="italic text-slate-200">
            {match[6]}
          </em>
        );
      }

      remaining = remaining.substring(match.index + match[0].length);
    }

    return parts;
  };

  const renderBlocks = () => {
    // Split by fenced code blocks: ```lang ... ```
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    const elements: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        const textChunk = content.substring(lastIndex, match.index);
        elements.push(renderTextParagraphs(textChunk, lastIndex));
      }

      const lang = match[1] || 'text';
      const code = match[2];
      elements.push(<CodeBlock key={`code-${match.index}`} language={lang} code={code} />);

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      elements.push(renderTextParagraphs(content.substring(lastIndex), lastIndex));
    }

    return elements;
  };

  const renderTextParagraphs = (text: string, baseKey: number) => {
    const lines = text.split('\n');
    const nodes: React.ReactNode[] = [];
    let listItems: string[] = [];
    let isOrderedList = false;

    const flushList = (idx: number) => {
      if (listItems.length > 0) {
        const ListTag = isOrderedList ? 'ol' : 'ul';
        nodes.push(
          <ListTag
            key={`list-${baseKey}-${idx}`}
            className={`my-2 space-y-1 text-slate-300 text-sm ${
              isOrderedList ? 'list-decimal list-inside' : 'list-disc list-inside'
            }`}
          >
            {listItems.map((item, liIdx) => (
              <li key={liIdx} className="leading-relaxed">
                {renderFormattedText(item)}
              </li>
            ))}
          </ListTag>
        );
        listItems = [];
      }
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Check for bullet list
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (isOrderedList) flushList(idx);
        isOrderedList = false;
        listItems.push(trimmed.substring(2));
        return;
      }

      // Check for numbered list
      const numMatch = trimmed.match(/^\d+\.\s+(.*)/);
      if (numMatch) {
        if (!isOrderedList) flushList(idx);
        isOrderedList = true;
        listItems.push(numMatch[1]);
        return;
      }

      // If non-list item, flush any existing list
      flushList(idx);

      if (trimmed === '') {
        return;
      }

      // Headers
      if (trimmed.startsWith('### ')) {
        nodes.push(
          <h3 key={`h3-${baseKey}-${idx}`} className="text-base font-semibold text-cyan-300 mt-4 mb-2">
            {renderFormattedText(trimmed.substring(4))}
          </h3>
        );
      } else if (trimmed.startsWith('## ')) {
        nodes.push(
          <h2 key={`h2-${baseKey}-${idx}`} className="text-lg font-bold text-slate-100 mt-5 mb-2">
            {renderFormattedText(trimmed.substring(3))}
          </h2>
        );
      } else if (trimmed.startsWith('# ')) {
        nodes.push(
          <h1 key={`h1-${baseKey}-${idx}`} className="text-xl font-extrabold text-white mt-6 mb-3">
            {renderFormattedText(trimmed.substring(2))}
          </h1>
        );
      } else {
        nodes.push(
          <p key={`p-${baseKey}-${idx}`} className="my-1.5 leading-relaxed text-slate-200 text-sm">
            {renderFormattedText(trimmed)}
          </p>
        );
      }
    });

    flushList(lines.length);
    return <div key={`chunk-${baseKey}`}>{nodes}</div>;
  };

  return <div className="space-y-1">{renderBlocks()}</div>;
};

interface CodeBlockProps {
  language: string;
  code: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-border-subtle bg-[#0c0d14]">
      <div className="flex items-center justify-between px-3 py-1.5 bg-background-tertiary border-b border-border-subtle text-xs text-slate-400">
        <span className="font-mono text-cyan-400">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-slate-200 transition-colors"
          title="Copy Code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="text-[11px]">{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <div className="p-3 overflow-x-auto text-xs font-mono text-slate-200 leading-normal">
        <pre>{code.trim()}</pre>
      </div>
    </div>
  );
};
