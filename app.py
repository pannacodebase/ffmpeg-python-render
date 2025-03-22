from flask import Flask, request, send_file, jsonify
import ffmpeg
import os
import shutil
import logging

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/combine', methods=['POST'])
def combine_files():
    if 'image' not in request.files or 'bg_music' not in request.files:
        logger.error("Missing image or bg_music")
        return jsonify({"error": "Missing image or bg_music"}), 400

    image_file = request.files['image']
    bg_music_file = request.files['bg_music']
    
    image_path = os.path.join(UPLOAD_FOLDER, 'test_image.jpg')
    bg_music_path = os.path.join(UPLOAD_FOLDER, 'background.mp3')
    output_file = os.path.join(UPLOAD_FOLDER, 'output_video.mp4')

    image_file.save(image_path)
    logger.info(f"Saved image: {image_path}")
    bg_music_file.save(bg_music_path)
    logger.info(f"Saved bg_music: {bg_music_path}")

    try:
        stream = ffmpeg.input(image_path, loop=1, t=5)  # 5-second image duration
        audio = ffmpeg.input(bg_music_path)
        output = ffmpeg.output(stream, audio, output_file, 
                              vcodec='libx264', acodec='aac', 
                              s='1280x720',  # Resize to 1280x720
                              r=25,          # Frame rate
                              t=5,           # 5-second video
                              shortest=None)
        logger.info("Running FFmpeg command")
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        if not os.path.exists(output_file) or os.path.getsize(output_file) < 1024:
            logger.error("Output file is empty or too small")
            return jsonify({"error": "FFmpeg produced no output"}), 500

        logger.info("FFmpeg completed successfully")
        response = send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name='output_video.mp4')
        shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        return response

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown FFmpeg error"
        logger.error(f"FFmpeg error: {error_msg}")
        return jsonify({"error": f"FFmpeg failed: {error_msg}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
