from flask import Flask, request, send_file, jsonify
import ffmpeg
import os
import shutil
import logging

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/combine', methods=['POST'])
def combine_files():
    if 'image' not in request.files or 'bgMusic' not in request.files:
        logger.error("Missing image or bgMusic")
        return jsonify({"error": "Missing image or bgMusic"}), 400

    image_file = request.files['image']
    bg_music_file = request.files['bgMusic']
    
    image_path = os.path.join(UPLOAD_FOLDER, f"img.{image_file.filename.split('.')[-1]}")
    bg_music_path = os.path.join(UPLOAD_FOLDER, 'bg.mp3')
    output_file = os.path.join(UPLOAD_FOLDER, 'output.mp4')

    image_file.save(image_path)
    logger.info(f"Saved image: {image_path}")
    bg_music_file.save(bg_music_path)
    logger.info(f"Saved bgMusic: {bg_music_path}")

    try:
        stream = ffmpeg.input(image_path, loop=1, t=5)  # 5-second image duration
        audio = ffmpeg.input(bg_music_path)
        output = ffmpeg.output(stream, audio, output_file, 
                              vcodec='libx264', acodec='aac', shortest=None, t=5)
        logger.info("Running FFmpeg command")
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        if not os.path.exists(output_file) or os.path.getsize(output_file) < 1024:
            logger.error("Output file is empty or too small")
            return jsonify({"error": "FFmpeg produced no output"}), 500

        logger.info("FFmpeg completed successfully")
        response = send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name='output.mp4')
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
