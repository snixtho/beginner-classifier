# Beginner Classifier

## Installation & Setup

- `pip install -r requirements.txt`
- [Optional] If you want logging to graylog, you must install graypy: `pip install graypy`
- Rename `conf.cfg.example` to `conf.cfg` and modify the settings to your requirements
- `python main.py -h` for usage information

## Usage
- Start the server `python main.py server`
	- If you get a bunch of errors from tensorflow about the gpu, you can ignore them.
	- If you don't use `--detach` and the server just closes immediately, an error occured. Check the log.
- Test the classifier using the server: `python  .\main.py classify --server --logins snixtho`
- For json output, use `--json`: `python  .\main.py classify --server --logins snixtho --json`
	- This will return a list of predictions in the array `predictions`. Each prediction contains a property `sucess` which is true on success, and false if an error occured. If an error occured, the property `error` contains details about what happened. Each prediction also contains the login requested as well as the predictions `experienced` and `beginner`. Their sum should be exactly 1, so the predicted class is the one with a higher value. The number itself is a indication about how sure the classifier is about it's prediction.
- To request multiple logins at the same time, just separate them by space: `python  .\main.py classify --server --logins snixtho brakerb tmexperte`

## Notes

- tensorflow 2.1.0 which is required, uses the AVX instruction set by default. If you get the error "Illegal Instruction", you can either configure your VM to use SandyBridge (if run in a VM) or build tensorflow from source.
- Coded and tested with python 3.6.