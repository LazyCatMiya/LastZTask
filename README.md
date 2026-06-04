# LastZ Task API Script

輸入玩家 id 後，腳本會依序呼叫貼上紀錄中的 LastZ store API：

- 七日簽到：`sendday7_new.php`
- 進入積分商城頁面：`getshop.php`
- 完成「登入」任務：`sendtask_new.php`
- 完成「瀏覽積分商城頁面」任務：`sendtask_new.php`
- 完成「首次購買金磚數量達到 2000」任務：`sendtask_new.php`
- 領取「每週特權禮包」：`sendvip.php`

請只對自己的帳號使用。

## 使用方式

### 跑固定名單

固定名單放在 `accounts.json`。可先從範例檔建立：

```bash
cp accounts.example.json accounts.json
```

先預覽全部帳號將送出的資料：

```bash
python3 run_daily_tasks.py --dry-run
```

真的執行固定名單：

```bash
python3 run_daily_tasks.py --insecure
```

不輸出執行 log：

```bash
python3 run_daily_tasks.py --insecure --quiet
```

之後要增加 id，在 `accounts.json` 新增一筆即可：

```json
{
  "name": "新名字",
  "uid": "1234567890000136"
}
```

如果要暫時停用某個帳號，可加上：

```json
{
  "name": "新名字",
  "uid": "1234567890000136",
  "enabled": false
}
```

### 跑單一帳號

先預覽將送出的資料，不真的呼叫 API：

```bash
python3 lastz_tasks.py 1556975198000136 --dry-run
```

真的執行：

```bash
python3 lastz_tasks.py 1556975198000136
```

如果你的 Python 出現 `SSL: CERTIFICATE_VERIFY_FAILED`，可先用以下方式暫時執行：

```bash
python3 lastz_tasks.py 1556975198000136 --insecure
```

`--insecure` 會跳過 HTTPS 憑證驗證，只建議在你信任目前網路時使用。較完整的做法是指定可信任的 CA 憑證檔：

```bash
python3 lastz_tasks.py 1556975198000136 --ca-file /path/to/ca.pem
```

不帶參數時會互動詢問玩家 id：

```bash
python3 lastz_tasks.py
```

可選參數：

```bash
python3 lastz_tasks.py 1556975198000136 --day 1 --vip-level 1 --delay 1.2
```

### 兌換不定期禮包碼

禮包碼每次不同時，不建議放進每日 CronJob。拿到 code 後手動跑一次即可，腳本會套用 `accounts.json` 的所有帳號：

```bash
python3 redeem_gift_code.py CELEBRATE300K --insecure
```

先預覽將送出的 GET URL：

```bash
python3 redeem_gift_code.py CELEBRATE300K --dry-run
```

不輸出執行 log：

```bash
python3 redeem_gift_code.py CELEBRATE300K --insecure --quiet
```

## GKE 定時執行

專案已附上 `Dockerfile` 和 `k8s/cronjob.yaml`。CronJob 預設每天台北時間 10:30 執行：

```yaml
schedule: "30 10 * * *"
timeZone: "Asia/Taipei"
```

請先建立本機 `.envrc`，或用 direnv 載入自己的環境設定：

```bash
cp .envrc.example .envrc
direnv allow
```

環境設定需提供：

```bash
export GCLOUD_ACCOUNT="service@example.com"
export PROJECT_ID="your-project"
export CLUSTER_NAME="your-cluster"
export CLUSTER_ZONE="asia-east1-b"
export IMAGE="asia-docker.pkg.dev/your-project/your-repository/last-task:latest"
```

一鍵建置、推送 image、部署 CronJob：

```bash
./scripts/deploy_gke.sh
```

如果要手動拆開跑，流程是：

```bash
gcloud config set account "$GCLOUD_ACCOUNT"
gcloud config set project "$PROJECT_ID"
gcloud auth configure-docker asia-docker.pkg.dev --quiet
gcloud container clusters get-credentials "$CLUSTER_NAME" \
  --zone "$CLUSTER_ZONE" \
  --project "$PROJECT_ID"

docker build --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"
sed "s#__IMAGE__#$IMAGE#g" k8s/cronjob.yaml | kubectl apply -f -
```

手動測試跑一次：

```bash
kubectl create job --from=cronjob/last-daily-tasks last-daily-tasks-manual
kubectl logs job/last-daily-tasks-manual
```

CronJob 預設帶 `--quiet`，所以正常情況下 `kubectl logs` 不會有輸出；請用 Job/Pod 狀態確認是否完成。

如果你的 GKE 版本不支援 `timeZone`，請移除 `timeZone: "Asia/Taipei"`，並把 schedule 改成 UTC 的 `30 2 * * *`。

## 本地定時執行

本地固定跑最簡單，適合每天會開機、有網路的機器。可以用 cron 或 macOS launchd 執行：

```bash
cd /path/to/LastZTask
python3 run_daily_tasks.py --insecure
```

GCP/GKE 比較適合想讓它不依賴自己電腦時使用。優點是穩定、可看 log，缺點是要多維護部署設定。
