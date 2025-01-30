import google.generativeai as genai
import boto3
import cv2
import whisper
import os
from PIL import ImageFont, ImageDraw, Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip
import ApiKey

# Initialisation des chemins et des configurations
genai.configure(api_key=ApiKey.getGeminiApiKey())
model = genai.GenerativeModel("gemini-1.5-flash")
repertoire = os.path.dirname(os.path.abspath(__file__))
NOM_FICHIER_VIDEO = 'JumpMc1.mp4'
NOM_FICHIER_AUDIO = 'test1.mp3'
NOM_FICHIER_VIDEO_CREE = 'VideoGenere.mp4'

# Vérification des fichiers nécessaires
if not os.path.exists(NOM_FICHIER_AUDIO):
    raise FileNotFoundError(f"CHEMIN AUDIO NON TROUVE")

if not os.path.exists(NOM_FICHIER_VIDEO):
    raise FileNotFoundError(f"CHEMIN VIDEO NON TROUVE")

# Chargement de la police
font_path = "police/LEMONMILK-Bold.otf"  # Remplacez par le chemin de votre fichier de police
if not os.path.exists(font_path):
    raise FileNotFoundError(f"Le fichier de police n'a pas été trouvé à l'emplacement spécifié : {font_path}")
font_size = 42  # Taille de la police
font = ImageFont.truetype(font_path, font_size)

def prompt_to_text(prompt):
    Daprompt = """Respond only with the raw audio text of the story generate only the audio without you doing an intro and an outro text ,
    Write a highly engaging and dramatic short story in the style of a Reddit post, formatted like a personal confession or an 'Am I the A**hole?' (AITA) post.
    The story should feature relatable but extraordinary situations, unexpected twists, and a strong emotional hook to captivate readers. Use an authentic, conversational tone 
    and include timestamps or small details to make it feel real. The story should spark debate or strong emotional reactions, making it perfect for sharing on TikTok or other 
    social media platforms.
    Examples of themes:
    Family drama with a shocking secret reveal.
    Workplace conflict that takes an unexpected turn.
    Relationship dilemmas with a jaw-dropping ending.
    A wholesome but surprising act of kindness or redemption.
    Make sure the story ends with a question or an open-ended conclusion to encourage discussion and also focus it aroud this theme :""" +prompt
    response = model.generate_content(Daprompt)
    try:
        return response.candidates[0].content.parts[0].text
    except (IndexError, AttributeError) as e:
        raise ValueError("Unexpected response structure") from e

def text_to_mp3(text, filename):
    session = boto3.Session(
        aws_access_key_id=ApiKey.getAWSAccessKeyId(),
        aws_secret_access_key=ApiKey.getAWSSecretAccessKey(),
        region_name="us-west-1"
    )
    polly = session.client('polly')
    reponse = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Joanna"
    )

    if 'AudioStream' in reponse:
        with open(filename, "wb") as file:
            file.write(reponse['AudioStream'].read())
            print(f"Le fichier suivant a été généré : {filename}")
            
def add_subtitles_to_video(video_path, audio_path, output_video_path):
    # Chargement du modèle Whisper pour la transcription
    model = whisper.load_model("base")

    # Transcription de l'audio
    print("Transcription de l'audio...")
    result = model.transcribe(audio_path)
    segments = [(segment['start'], segment['end'], segment['text']) for segment in result['segments']]

    # Vérification des segments
    print(f"Nombre de segments transcrits: {len(segments)}")
    for i, (start, end, text) in enumerate(segments[:5]):  # Afficher les 5 premiers segments
        print(f"Segment {i}: Début={start}, Fin={end}, Texte='{text}'")

    # Chargement de la vidéo
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # Création d'un fichier temporaire pour la vidéo
    temp_output_video_path = "temp_video.mp4"
    out = cv2.VideoWriter(temp_output_video_path, fourcc, fps, (width, height))
    frame_count = 0
    LimiteVideoOneMinute = fps * 60
    print(LimiteVideoOneMinute)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print(f"Fin de la lecture vidéo après {frame_count} frames.")
            break

        # Ajout des sous-titres si le frame est dans l'intervalle d'un segment
        for start, end, text in segments:
            start_frame = int(start * fps)
            end_frame = int(end * fps)

            # Débogage : Afficher les sous-titres ajoutés
            if start_frame <= frame_count <= end_frame:
                print(f"Ajout du texte '{text}' dans l'intervalle {start_frame}-{end_frame} (frame {frame_count})")

                # Diviser le texte en plusieurs lignes si nécessaire
                words = text.split()
                lines = []
                current_line = ""

                for word in words:
                    test_line = current_line + word + " "
                    img_pil = Image.fromarray(frame)
                    draw = ImageDraw.Draw(img_pil)
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    if text_width > width:
                        lines.append(current_line.strip())
                        current_line = word + " "
                    else:
                        current_line = test_line

                if current_line:
                    lines.append(current_line.strip())

                # Calculer la position verticale pour centrer les lignes
                total_height = len(lines) * (text_height + 10)  # 10 pixels de marge entre les lignes
                start_y = (height - total_height) // 2

                # Ajouter chaque ligne de texte avec contour
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = (width - text_width) // 2

                    # Dessiner le contour noir
                    draw.text((text_x-2, start_y-2), line, font=font, fill=(0, 0, 0))
                    draw.text((text_x+2, start_y-2), line, font=font, fill=(0, 0, 0))
                    draw.text((text_x-2, start_y+2), line, font=font, fill=(0, 0, 0))
                    draw.text((text_x+2, start_y+2), line, font=font, fill=(0, 0, 0))

                    # Dessiner le texte principal
                    draw.text((text_x, start_y), line, font=font, fill=(255, 255, 255))
                    start_y += text_height + 10  # Déplacer vers le bas pour la ligne suivante

                frame = np.array(img_pil)

        if frame_count >= LimiteVideoOneMinute:
            print("Limite d'une minute atteinte.")
            break

        out.write(frame)
        frame_count += 1

    # Cleanup block to ensure resources are properly released
    if cap.isOpened():
        cap.release()
    if out.isOpened():
        out.release()

    print("Ajout de l'audio à la vidéo...")
    original_video = VideoFileClip(temp_output_video_path).subclip(0, 60)  # Limiter la vidéo à 60 secondes
    original_audio = AudioFileClip(audio_path).subclip(0, 60)  # Limiter l'audio à 60 secondes
    final_video = original_video.set_audio(original_audio)
    final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

    # Suppression du fichier temporaire
    if os.path.exists(temp_output_video_path):
        os.remove(temp_output_video_path)

    print(f"Vidéo avec sous-titres générée : {output_video_path}")

text = prompt_to_text('A story about Margot being a bot')
filename = NOM_FICHIER_AUDIO
text_to_mp3(text, filename)
audio_path = os.path.join(repertoire, NOM_FICHIER_AUDIO)
video_path = os.path.join(repertoire, NOM_FICHIER_VIDEO)
output_video_path = NOM_FICHIER_VIDEO_CREE
add_subtitles_to_video(video_path, audio_path, output_video_path)
