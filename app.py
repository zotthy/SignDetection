import torch
from ultralytics import YOLO
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image, ImageDraw, ImageTk
from gtts import gTTS
import os
import subprocess
import tkinter as tk
from tkinter import filedialog

device = "mps" if torch.backends.mps.is_available() else "cpu"


YOLO_PATH = ''

print("Ładowanie modeli... Proszę czekać.")
model = YOLO(YOLO_PATH).to(device)
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
model_ocr = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed').to(device)

class SignApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detektor Znaków Drogowych")
        self.root.geometry("800x700")

        # Elementy GUI
        self.label_title = tk.Label(root, text="System Rozpoznawania Znaków", font=("Arial", 20))
        self.label_title.pack(pady=10)

        self.btn_load = tk.Button(root, text="Wybierz zdjęcie", command=self.load_and_process, font=("Arial", 14))
        self.btn_load.pack(pady=10)

        self.canvas = tk.Label(root) # Tu wyświetlimy obrazek
        self.canvas.pack(pady=10)

        self.status = tk.Label(root, text="Gotowy", fg="blue")
        self.status.pack(side="bottom", fill="x")

    def load_and_process(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        self.status.config(text="Przetwarzanie...")
        self.root.update()


        results = model.predict(file_path, conf=0.5, device=device)
        img = Image.open(file_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        found_signs = []

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls)
                label = model.names[class_id]

                if label == 'speedlimit':
                    crop = img.crop((max(0, x1-5), max(0, y1-5), x2+5, y2+5))
                    pixel_values = processor(images=crop, return_tensors="pt").pixel_values.to(device)
                    generated_ids = model_ocr.generate(pixel_values)
                    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                    
                    clean_text = ''.join(filter(str.isdigit, text))
                    display_label = f"Ograniczenie do {clean_text}" if clean_text else "Ograniczenie prędkości"
                else:
                    labels_pl = {"stop": "Stop", "crosswalk": "Przejście dla pieszych", "trafficlight": "Sygnalizacja świetlna"}
                    display_label = labels_pl.get(label, label)

                found_signs.append(display_label)
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                draw.text((x1, y1 - 10), display_label, fill="red")

        # Wyświetlanie w oknie
        img.thumbnail((600, 450)) # Zmniejszamy podgląd do okna
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.config(image=self.photo)

        # Głos
        if found_signs:
            txt = "Wykryto: " + ", ".join(found_signs)
            self.status.config(text=txt)
            tts = gTTS(text=txt, lang='pl')
            tts.save("audio.mp3")
            subprocess.run(["afplay", "audio.mp3"]) # Odtwarzanie na macOS
        else:
            self.status.config(text="Nie wykryto znaków.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SignApp(root)
    root.mainloop()