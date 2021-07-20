from flask import Flask, request
import EPFO_Scraper
import os

app = Flask(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "client_secrets.json"

@app.route('/epfo/', methods=['GET'])
def org_search_details():
    org_name = request.args.get('org_name')
    f_emp_name = request.args.get('f_emp_name')
    l_emp_name = request.args.get('l_emp_name')
    org_code = request.args.get('code')

    c = "Invalid Captcha"
    while c == "Invalid Captcha" :
        c = EPFO_Scraper.main(org_name, f_emp_name, l_emp_name, org_code)
    return c


if __name__ == '__main__':
    app.run(debug=True)
