import jwt from "jsonwebtoken";
import bcrypt from 'bcrypt'

export const comparePassword = (password, hash) => {
    return bcrypt.compare(password, hash)
}

export const hashPassword = (password) =>{
    //the 2nd argument is the salt
    return bcrypt.hash(password, 5)
}

export const createJWT = (user) => {
  const token = jwt.sign(
    {
      id: user.id,
      username: user.username,
    },
    process.env.JWT_SECRET
  );

    return token;
};

export const protect = (req,res, next)=>{
    const bearer = req.headers.authorization

    if(!bearer) {
        res.status(401)
        res.json({message: 'not authorized - no auth headers'})
        return 
    }

    const [,token] = bearer.split(' ');

    if(!token){
        res.status(401)
        res.json({message: 'not authorized - no bearer token'})
        return 
    }

    try{
        const user = jwt.verify(token, process.env.JWT_SECRET)
        req.user = user
        next()
    }catch(e){
        console.error("error while verifying token ",e)
        res.status(401)
        res.json({message: 'not authorized - not a valid token'})
        return 
    }

}

