export default function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-gray-950 py-8" id="footer">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white font-bold text-xs">
              S
            </div>
            <span className="text-sm text-slate-400">
              <span className="text-slate-300 font-semibold">SwingMaster</span> — AI 골프 코치
            </span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6 text-xs text-slate-500">
            <a href="#" className="hover:text-slate-300 transition-colors">이용약관</a>
            <a href="#" className="hover:text-slate-300 transition-colors">개인정보처리방침</a>
            <a href="#" className="hover:text-slate-300 transition-colors">문의</a>
          </div>

          {/* Copyright */}
          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} Swing Master. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
