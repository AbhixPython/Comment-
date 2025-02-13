from flask import Flask, render_template, request, jsonify
import facebook
import time
import threading

app = Flask(__name__)
tasks = {}

def post_comments(hater_name, post_id, comments, cookies):
    success_count = 0
    error_messages = []
    try:
        for cookie in cookies:
            access_token = cookie.strip()
            if not access_token:
                continue

            try:
                graph = facebook.GraphAPI(access_token)
                for comment in comments:
                    try:
                        graph.put_object(post_id, "comments", message=f"To {hater_name}: {comment}")
                        time.sleep(2)  # Adjust delay as needed
                        success_count += 1
                    except facebook.GraphAPIError as e:
                        error_message = f"Facebook API Error: {e} (for token starting with {access_token[:10]}...): Comment: {comment[:50]}..."
                        print(error_message)
                        error_messages.append(error_message)

                        if "OAuthException" in str(e):
                            break
                        elif "RateLimitingException" in str(e):
                            time.sleep(60)
                            continue
                        else:
                            return jsonify({'error': f"Facebook API Error: {e}", 'success_count': success_count, 'error_messages': error_messages}), 500
            except Exception as e:
                error_message = f"Error initializing Graph API: {e} (for token starting with {access_token[:10]}...)"
                print(error_message)
                error_messages.append(error_message)
                continue

        return jsonify({'message': f'Comments posted (or attempted) with {success_count} successful posts.', 'success_count': success_count, 'error_messages': error_messages}), 200

    except Exception as e:
        return jsonify({'error': str(e), 'success_count': success_count, 'error_messages': error_messages}), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        hater_name = request.form.get('hater_name')
        post_id = request.form.get('post_id')
        comment_file = request.files.get('comment_file')
        cookie_file = request.files.get('cookie_file')

        if not all([hater_name, post_id, comment_file, cookie_file]):
            return jsonify({'error': 'All fields are required'}), 400

        try:
            comments = [line.decode('utf-8').strip() for line in comment_file.stream]
            cookies = [line.decode('utf-8').strip() for line in cookie_file.stream]

            task_id = f"{time.time()}"
            task = threading.Thread(target=post_comments, args=(hater_name, post_id, comments, cookies))
            tasks[task_id] = task
            task.start()

            return jsonify({'message': 'Task started', 'task_id': task_id}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('index.html')


@app.route('/stop_task', methods=['POST'])
def stop_task():
    task_id = request.form.get('task_id')
    if task_id and task_id in tasks:
        del tasks[task_id]  # Remove task; thread will eventually stop if it's still running.
        return jsonify({'message': f'Task {task_id} stopping (if still running).'}), 200
    return jsonify({'error': 'Invalid task ID'}), 400


if __name__ == '__main__':
    app.run(debug=True)
