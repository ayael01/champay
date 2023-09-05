import boto3
from flask import Flask, jsonify

app = Flask(__name__)

# Initialize the boto3 client for SES
ses_client = boto3.client('ses', region_name='eu-north-1')


@app.route('/send_email', methods=['GET'])
def send_email():
    try:
        response = ses_client.send_email(
            Source='no-reply@cham-pay.com',
            Destination={
                'ToAddresses': ['ayael01@gmail.com'],
            },
            Message={
                'Subject': {
                    'Data': 'Hello from Champay',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': 'Hello! This is a test email from Champay using Amazon SES.',
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        # If the above function call does not throw an exception, it means the email was sent successfully.
        return jsonify({"message": "Email sent successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
