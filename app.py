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
    if 'images' not in request.files or 'bgMusic' not in request.files:
        logger.error("Missing images or bgMusic")
        return jsonify({"error": "Missing images or bgMusic"}), 400

    image_files = request.files.getlist('images')
    bg_music_file = request.files['bgMusic']
    
    image_paths = []
    for i, img in enumerate(image_files):
        path = os.path.join(UPLOAD_FOLDER, f"img{i}.{img.filename.split('.')[-1]}")
        img.save(path)
        image_paths.append(path)
        logger.info(f"Saved image: {path}")
    
    bg_music_path = os.path.join(UPLOAD_FOLDER, 'bg.mp3')
    bg_music_file.save(bg_music_path)
    logger.info(f"Saved bgMusic: {bg_music_path}")

    output_file = os.path.join(UPLOAD_FOLDER, f"output-{os.urandom(4).hex()}.mp4")
    logger.info(f"Output file will be: {output_file}")

    try:
        # Simplify: Resize to 1280x720 and avoid complex filters
        stream = ffmpeg.input(image_paths[0], loop=1, t=5)
        for img in image_paths[1:]:
            stream = ffmpeg.concat(stream, ffmpeg.input(img, loop=1, t=5), v=1, a=0)
        audio = ffmpeg.input(bg_music_path)
        output = ffmpeg.output(stream, audio, output_file, 
                              vcodec='libx264', acodec='aac', 
                              s='1280x720',  # Set size directly in output
                              r=25,          # Frame rate
                              t=len(image_paths) * 5,  # Duration
                              shortest=None)
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
