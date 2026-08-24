const express = require("express");
const cors = require("cors");
const multer = require("multer");
const sqlite3 = require("sqlite3").verbose();
const path = require("path");

const app = express();

app.use(cors());
app.use(express.json());


// پوشه عکس رسید
const upload = multer({
    dest: "receipts/"
});


// دیتابیس
const db = new sqlite3.Database(
    "dogs.db"
);


// ساخت جدول کاربران
db.run(`
CREATE TABLE IF NOT EXISTS users(
id TEXT PRIMARY KEY,
balance INTEGER DEFAULT 10000
)
`);


// ساخت جدول واریز
db.run(`
CREATE TABLE IF NOT EXISTS deposits(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id TEXT,
amount INTEGER,
photo TEXT,
status TEXT
)
`);



// صفحه تست
app.get("/",(req,res)=>{

    res.send(
        "🚀 DOGS LIMBO SERVER ONLINE"
    );

});



// گرفتن موجودی
app.get("/balance/:id",(req,res)=>{

    let id=req.params.id;


    db.get(
    `
    SELECT balance 
    FROM users
    WHERE id=?
    `,
    [id],
    (err,row)=>{


        if(!row){

            db.run(
            `
            INSERT INTO users(id,balance)
            VALUES(?,10000)
            `,
            [id]
            );


            return res.json({
                balance:10000
            });

        }


        res.json({
            balance:row.balance
        });


    });

});




// ثبت واریز مجازی
app.post(
"/deposit",
upload.single("photo"),
(req,res)=>{


    let user_id=req.body.user_id;

    let amount=req.body.amount;


    if(!user_id || !amount || !req.file){

        return res.json({
            error:"اطلاعات ناقص است"
        });

    }



    db.run(
    `
    INSERT INTO deposits
    (user_id,amount,photo,status)

    VALUES(?,?,?,?,)
    `,
    [
        user_id,
        amount,
        req.file.path,
        "pending"
    ],
    );


    res.json({

        success:true,

        message:
        "رسید ارسال شد"

    });


});





// لیست درخواست های تایید نشده
app.get(
"/admin/deposits",
(req,res)=>{


db.all(
`
SELECT *
FROM deposits
WHERE status='pending'
`,
[],
(err,rows)=>{


res.json(rows);


});


});






// تایید واریز
app.post(
"/admin/approve",
(req,res)=>{


let id=req.body.id;



db.get(
`
SELECT *
FROM deposits
WHERE id=?
`,
[id],
(err,row)=>{


if(!row){

return res.json({
error:"نداریم"
});

}



db.run(
`
UPDATE users
SET balance=balance+?
WHERE id=?
`,
[
row.amount,
row.user_id
]
);



db.run(
`
UPDATE deposits
SET status='approved'
WHERE id=?
`,
[id]
);



res.json({
success:true
});


});


});






// رد واریز
app.post(
"/admin/reject",
(req,res)=>{


db.run(
`
UPDATE deposits
SET status='rejected'
WHERE id=?
`,
[
req.body.id
]
);


res.json({
success:true
});


});





const PORT =
process.env.PORT || 3000;


app.listen(
PORT,
()=>{

console.log(
"SERVER RUNNING PORT "+PORT
);

});
