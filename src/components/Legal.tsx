import React from 'react';
import { ArrowLeft, ShieldCheck, Scale, Lock, FileText } from 'lucide-react';

interface LegalProps {
  onBack: () => void;
}

export function Legal({ onBack }: LegalProps) {
  const sections = [
    {
      title: 'Terms & Conditions',
      icon: Scale,
      content: `Welcome to Nexus. By accessing our platform, you agree to be bound by these terms. Nexus provides educational resources and business tools. 
      
      1. Use of Platform: You must be at least 18 years old to use this service.
      2. Educational Nature: All content is for educational purposes. We do not provide financial, legal, or tax advice.
      3. Account Security: You are responsible for maintaining the confidentiality of your account credentials.
      4. Intellectual Property: All platform content is owned by Nexus or its licensors.`
    },
    {
      title: 'Privacy Policy',
      icon: Lock,
      content: `Your privacy is paramount. We collect information to provide and improve our services.
      
      1. Data Collection: We collect contact information, business details, and usage data.
      2. Data Usage: We use your data to personalize your experience and communicate updates.
      3. Data Protection: We implement industry-standard security measures to protect your information.
      4. Third Parties: We do not sell your personal data to third parties.`
    },
    {
      title: 'Financial Disclosures',
      icon: ShieldCheck,
      content: `Nexus is not a financial institution or a registered investment advisor.
      
      - No Guarantees: We do not guarantee any specific financial outcome, funding approval, or credit score increase.
      - Risk Acknowledgment: Business ventures and trading involve significant risk.
      - Professional Consultation: Users are encouraged to seek advice from licensed professionals.`
    }
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFF] py-12 px-4 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-[#5B7CFA] transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span className="text-[10px] font-black uppercase tracking-widest">Back to Portal</span>
        </button>

        <div className="text-center space-y-4">
          <h1 className="text-3xl font-black text-[#1A2244]">Legal & Compliance</h1>
          <p className="text-sm text-slate-500 font-medium">Transparency and trust are the foundation of Nexus.</p>
        </div>

        <div className="space-y-6">
          {sections.map((section) => (
            <div key={section.title} className="glass-card p-8 space-y-6">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                  <section.icon className="w-5 h-5" />
                </div>
                <h2 className="text-xl font-black text-[#1A2244]">{section.title}</h2>
              </div>
              <div className="prose prose-slate max-w-none">
                <p className="text-sm text-slate-600 font-medium leading-relaxed whitespace-pre-line">
                  {section.content}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center pt-8">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Last Updated: April 15, 2025
          </p>
        </div>
      </div>
    </div>
  );
}
