package gt.gob.munisoke.sirec;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

import com.opensymphony.xwork2.ActionSupport;

/** Acceso de operadores de SIREC (oficina de la muni FICTICIA). Claves en MD5 sin sal, como en el sistema original. */
public class LoginAction extends ActionSupport {
    private String usuario, clave, nombre, rol;

    @Override
    public String execute() throws Exception {
        if (usuario == null || clave == null || usuario.isEmpty()) {
            addActionError("Escribe tu usuario y tu clave.");
            return INPUT;
        }
        String md5 = String.format("%032x", new BigInteger(1, MessageDigest.getInstance("MD5").digest(clave.getBytes(StandardCharsets.UTF_8))));
        Class.forName("com.mysql.jdbc.Driver");
        try (Connection c = DriverManager.getConnection("jdbc:mysql://sirec-db:3306/sirec?useSSL=false", "sirec", "sirec2014");
             PreparedStatement ps = c.prepareStatement("SELECT nombre, rol FROM usuarios_sirec WHERE usuario = ? AND clave_md5 = ?")) {
            ps.setString(1, usuario);
            ps.setString(2, md5);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    nombre = rs.getString(1);
                    rol = rs.getString(2);
                    return SUCCESS;
                }
            }
        }
        addActionError("Usuario o clave incorrectos.");
        return INPUT;
    }

    public String getUsuario() { return usuario; }
    public void setUsuario(String u) { usuario = u; }
    public void setClave(String c) { clave = c; }
    public String getNombre() { return nombre; }
    public String getRol() { return rol; }
}
