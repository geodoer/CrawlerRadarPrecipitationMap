polygons[id].fire("click"); //table 触发 polygon

        var checked = $(this).is(':checked');
        if (checked==true) {
            // 全选
            $('input:checkbox').attr("checked", true);
        } else {
            // 全部不选
            $('input:checkbox').attr("checked", false);
        }