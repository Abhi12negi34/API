import sys
import os
sys.path.append(os.getcwd())
from reports.generators.pdf_generator import PDFReportGenerator

raw_results = {
    "usability": {"findings": {"f1": {"success": True, "log": "test", "path": "/test"}}},
    "security": {"findings": {"f2": {"success": True, "log": "test", "path": "/test"}}},
    "efficiency": {"findings": {"f3": {"success": True, "log": "test", "path": "/test"}}},
    "reliability": {"findings": {"f4": {"success": True, "log": "test", "path": "/test"}}},
    "performance": {"findings": {"f5": {"success": True, "log": "test", "path": "/test"}}},
    "accessibility": {"findings": {"f6": {"success": True, "log": "test", "path": "/test"}}},
    "scalability": {"findings": {"f7": {"success": True, "log": "test", "path": "/test"}}},
    "stability": {"findings": {"f8": {"success": True, "log": "test", "path": "/test"}}},
    "metadata": {"discovery_baseline": []}
}
scorecard = {k: {"attribute_score": 100, "weight": 0.125, "passed": 1, "total_tools": 1, "blockers": 0} for k in ["usability", "security", "efficiency", "reliability", "performance", "accessibility", "scalability", "stability"]}

gen = PDFReportGenerator()
try:
    gen.generate(raw_results, scorecard, 100, "Platinum", "test_report.pdf")
    print("PDF Success")
except Exception as e:
    print(f"PDF Failed: {str(e)}")
    import traceback
    traceback.print_exc()
