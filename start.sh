if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/sandippshah/RxSpamBot.git /RxSpamBot 
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /RxSpamBot 
fi
cd /RxSpamBot
pip3 install -U -r requirements.txt
echo "Starting Bot...."
python3 p3.py