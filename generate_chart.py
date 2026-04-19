import requests

dot = """
digraph G {
  rankdir=TB;
  fontname="Helvetica,Arial,sans-serif";
  node [fontname="Helvetica,Arial,sans-serif", shape=box, style=filled, fillcolor="#f8f9fa", color="#ced4da", penwidth=2];
  edge [fontname="Helvetica,Arial,sans-serif", color="#007bff", penwidth=1.5];
  
  Start [shape=oval, fillcolor="#28a745", fontcolor="white", color="#218838", label="START"];
  End [shape=oval, fillcolor="#dc3545", fontcolor="white", color="#c82333", label="END"];
  
  Start -> "Access Clinical Couture";
  "Access Clinical Couture" -> "Is Registered?" [arrowhead=vee];
  
  "Is Registered?" [shape=diamond, fillcolor="#ffc107", color="#e0a800", height=0.8];
  
  "Is Registered?" -> "Register" [label=" No "];
  "Is Registered?" -> "Login" [label=" Yes "];
  "Register" -> "Login" [arrowhead=vee];
  
  "Login" -> "Role-Based Redirection" [arrowhead=vee];
  "Role-Based Redirection" [shape=diamond, fillcolor="#17a2b8", fontcolor="white", color="#138496", height=0.8];
  
  "Role-Based Redirection" -> "Patient Dashboard" [label=" Patient "];
  "Role-Based Redirection" -> "Doctor Dashboard" [label=" Doctor "];
  "Role-Based Redirection" -> "Admin Dashboard" [label=" Admin "];
  
  subgraph cluster_Patient {
      label="Patient Flow";
      fontname="Helvetica-Bold";
      style=dashed;
      color="#007bff";
      "Patient Dashboard" -> "Book Appointment" -> "AI Chat Triage" -> "Geolocation Mapping" -> "Select Doctor" -> "Doctor Available?";
      "Doctor Available?" [shape=diamond, fillcolor="#ffc107", color="#e0a800", margin=0.2];
      "Doctor Available?" -> "Save to Database" [label=" Yes "];
      "Save to Database" -> "Email Confirmation" -> "Queue Privacy Masking" -> End;
      "Doctor Available?" -> "Emergency Connect / Retry" [label=" No "];
      "Emergency Connect / Retry" -> End;
  }
  
  subgraph cluster_Doctor {
      label="Doctor Flow";
      fontname="Helvetica-Bold";
      style=dashed;
      color="#28a745";
      "Doctor Dashboard" -> "View Patient Queue" -> "Mark Consultation Status" -> End;
  }
  
  subgraph cluster_Admin {
      label="Admin Flow";
      fontname="Helvetica-Bold";
      style=dashed;
      color="#6c757d";
      "Admin Dashboard" -> "Manage Clinics & Logs" -> End;
  }
}
"""

res = requests.post('https://quickchart.io/graphviz', json={"graph": dot, "format": "png"})
with open('Clinical_Couture_System_Flowchart.png', 'wb') as f:
    f.write(res.content)
print("Saved Clinical_Couture_System_Flowchart.png successfully!")
