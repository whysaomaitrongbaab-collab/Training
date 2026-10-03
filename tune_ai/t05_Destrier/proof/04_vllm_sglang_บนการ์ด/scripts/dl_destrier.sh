#!/bin/bash
# โหลด dacarokann/destrier rev e229403 แบบแบ่ง 16 ช่วงขนาน — snapshot_download ดึงไฟล์เดียว 11 GB ทีละเส้นได้ ~5 MB/s
# (hub 1.30 เลิก hf_transfer แล้ว · Xet ปิดไว้เพราะพังกลางโหลดเมื่อ 23 ก.ย.) · ตรวจ sha256 กับที่ HF ประกาศ
set -u
REV=e229403b12f63794217290c199fc5a069aea5b78
B=https://huggingface.co/dacarokann/destrier/resolve/$REV
D=/workspace/destrier_src; mkdir -p $D/parts; cd $D
for f in adapter_config.json README.md tokenizer.json tokenizer_config.json chat_template.jinja; do
  curl -sfL -o $f "$B/$f" || rm -f $f
done
ls $D
H=$(curl -sIL "$B/adapter_model.safetensors" | tr -d '\r')
SIZE=$(echo "$H" | grep -i '^x-linked-size:' | tail -1 | awk '{print $2}')
SHA=$(echo "$H" | grep -i '^x-linked-etag:' | tail -1 | awk '{print $2}' | tr -d '"')
echo "size=$SIZE sha=$SHA"
[ -n "$SIZE" ] || { echo "ไม่รู้ขนาดไฟล์"; exit 1; }
N=16; CH=$(( (SIZE + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  S=$((i*CH)); E=$((S+CH-1)); [ $E -ge $SIZE ] && E=$((SIZE-1))
  ( for t in 1 2 3 4 5; do
      curl -sfL --retry 5 -r $S-$E -o parts/p$i "$B/adapter_model.safetensors" \
        && [ $(stat -c %s parts/p$i) -eq $((E-S+1)) ] && break
      echo "ช่วง $i ลองใหม่ $t"; rm -f parts/p$i; sleep 5
    done ) &
done
wait
cat $(for i in $(seq 0 $((N-1))); do echo parts/p$i; done) > adapter_model.safetensors && rm -rf parts
GOT=$(sha256sum adapter_model.safetensors | awk '{print $1}')
echo "sha256 $GOT"
[ "$GOT" = "$SHA" ] && echo SHA_OK || { echo SHA_MISMATCH; exit 1; }
