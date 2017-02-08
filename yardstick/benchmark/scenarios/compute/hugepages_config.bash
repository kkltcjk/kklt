# this script is used to config hugepagesz in cmdline
set -x
cp /etc/default/grub /etc/default/grub_bak
echo 'GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX default_hugepagesz=1GB hugepagesz=1G hugepages=8 transparent_hugepage=never"' >> /etc/default/grub
which grub2-mkconfig
if [ $? -eq 0 ]; then
    grub2-mkconfig -o /boot/grub2/grub.cfg
else
    which grub-mkconfig
    if [ $? -eq 0 ]; then
        grub-mkconfig -o /boot/grub/grub.cfg
    else
        echo "not find grub-mkconfig"
        exit -1
    fi
fi
# recovery
cp /etc/default/grub_bak /etc/default/grub
reboot

