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
    if 'image1' not in request.files or 'image2' not in request.files or 'bg_music' not in request.files:
        logger.error("Missing image1, image2, or bg_music")
        return jsonify({"error": "Missing image1, image2, or bg_music"}), 400

    image1_file = request.files['image1']
    image2_file = request.files['image2']
    bg_music_file = request.files['bg_music']
    
    image1_path = os.path.join(UPLOAD_FOLDER, 'image1.jpg')
    image2_path = os.path.join(UPLOAD_FOLDER, 'image2.jpg')
    bg_music_path = os.path.join(UPLOAD_FOLDER, 'background.mp3')
    output_file = os.path.join(UPLOAD_FOLDER, 'output_video.mp4')

    image1_file.save(image1_path)
    logger.info(f"Saved image1: {image1_path}")
    image2_file.save(image2_path)
    logger.info(f"Saved image2: {image2_path}")
    bg_music_file.save(bg_music_path)
    logger.info(f"Saved bg_music: {bg_music_path}")

    try:
        # Define target resolution
        target_resolution = '1280x720'

        # Input streams for both images, each 5 seconds, with scaling
        stream1 = ffmpeg.input(image1_path).filter('scale', size=target_resolution, force_original_aspect_ratio='decrease').filter('pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2').filter('setsar', 1).filter('loop', loop=1, size=125, duration=5)  # 25 fps × 5s = 125 frames
        stream2 = ffmpeg.input(image2_path).filter('scale', size=target_resolution, force_original_aspect_ratio='decrease').filter('pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2').filter('setsar', 1).filter('loop', loop=1, size=125, duration=5)  # 25 fps × 5s = 125 frames

        # Concatenate images into a slideshow
        video = ffmpeg.concat(stream1, stream2, v=1, a=0)
        audio = ffmpeg.input(bg_music_path)

        # Output with video and audio
        output = ffmpeg.output(video, audio, output_file, 
                              vcodec='libx264', acodec='aac', 
                              r=25,          # Frame rate
                              t=10,          # 10 seconds total (2 images × 5s)
                              shortest=None) # Use full 10s duration
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
