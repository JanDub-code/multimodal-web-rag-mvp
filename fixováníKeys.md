1) Nejrychlejší fix pro Docker (zaručeně se propíše do kontejneru)


cd /home/hans/Downloads/mvp
read -s -p "OPENCODE_API_KEY: " OPENCODE_API_KEY; echo
export OPENCODE_API_KEY
docker compose up -d --force-recreate --no-deps api

docker compose exec -T api sh -lc 'test -n "$OPENCODE_API_KEY" && echo OK || echo MISSING'
curl -fsS http://127.0.0.1:8000/health | python -m json.tool | grep configured



2) Globálně (pro všechny nové terminály + funguje i mimo Docker)


mkdir -p ~/.config/mvp && chmod 700 ~/.config/mvp
read -s -p "OPENCODE_API_KEY: " key; echo
printf 'export OPENCODE_API_KEY=%q\n' "$key" > ~/.config/mvp/opencode_key.sh
chmod 600 ~/.config/mvp/opencode_key.sh

grep -q 'opencode_key.sh' ~/.bashrc || echo 'source ~/.config/mvp/opencode_key.sh' >> ~/.bashrc
grep -q 'opencode_key.sh' ~/.profile || echo 'source ~/.config/mvp/opencode_key.sh' >> ~/.profile
source ~/.config/mvp/opencode_key.sh
unset key