

class Mqtt5Service:

    # sps_type:
    # 0     exact
    # 1     from ... to

    # Message types:
    # 0     No error (status)
    # 1     INFO
    # 2     WARNING
    # 3     ERROR

    #@SerializedName("id")       var id: Int? = -1,
    #@SerializedName("status")   var status : MessageType? = MessageType.STATUS,
    #@SerializedName("time")     var time: Long = 0,
    #@SerializedName("sps")      var sps: Int? = -1,
    #@SerializedName("group")    var group: Int? = -1,
    #@SerializedName("device")   var device: String? = "00",
    #@SerializedName("part")     var part: Int? = -1,
    #@SerializedName("message")  var message: String? = ""


    def setup(self):
        a = ""