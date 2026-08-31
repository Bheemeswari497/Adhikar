import "@/App.css";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { Landmark, Upload, Map, LayoutList } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import DashboardPage from "@/pages/DashboardPage";
import UploadPage from "@/pages/UploadPage";
import MapPage from "@/pages/MapPage";
import RecordDetailPage from "@/pages/RecordDetailPage";

const navCls = ({ isActive }) =>
  `flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
  }`;

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-white text-zinc-900">
        <header className="border-b border-zinc-200 bg-white sticky top-0 z-[1100]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-zinc-900 text-white rounded-md flex items-center justify-center">
                <Landmark size={20} />
              </div>
              <div>
                <h1 className="font-heading text-lg font-bold tracking-tight leading-none">Adhikar</h1>
                <p className="text-[11px] text-zinc-500 uppercase tracking-[0.12em]">Land Record Validation</p>
              </div>
            </div>
            <nav className="flex items-center gap-1">
              <NavLink to="/" end className={navCls} data-testid="nav-dashboard">
                <LayoutList size={16} /> <span className="hidden sm:inline">Dashboard</span>
              </NavLink>
              <NavLink to="/upload" className={navCls} data-testid="nav-upload">
                <Upload size={16} /> <span className="hidden sm:inline">Upload &amp; OCR</span>
              </NavLink>
              <NavLink to="/map" className={navCls} data-testid="nav-map">
                <Map size={16} /> <span className="hidden sm:inline">Parcel Map</span>
              </NavLink>
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/records/:id" element={<RecordDetailPage />} />
          </Routes>
        </main>
        <Toaster position="top-right" richColors />
      </div>
    </BrowserRouter>
  );
}

export default App;
