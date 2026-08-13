from fpdf import FPDF
try:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(40, 10, "Hello World")
    pdf.output("test_font.pdf")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
